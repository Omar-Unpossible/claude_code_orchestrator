# LLM-First Prompt Engineering Framework

**Document Type**: Design Specification
**Status**: Draft for Review
**Date**: 2025-11-03
**Author**: AI Design Analysis
**Purpose**: Design a comprehensive rule-based prompt engineering system optimized for LLM-to-LLM communication

---

## Executive Summary

This document proposes a systematic prompt engineering framework for Obra that optimizes communication between the Qwen supervisor (Obra) and Claude Code execution agent (rAI). The framework shifts from human-centered natural language prompts to machine-optimized structured formats, implements domain-specific prompt rules, and provides complexity estimation for intelligent task breakdown.

**Key Objectives**:
1. Standardize prompt structure across all interaction types
2. Implement machine-optimized formats (JSON/structured data) for LLM-to-LLM communication
3. Define domain-specific rules for code generation, documentation, task planning, testing
4. Enable complexity estimation and automatic task decomposition
5. Support parallel agent deployment for independent tasks
6. Eliminate human-centered design decisions in favor of LLM-first optimization

---

## 1. Current State Analysis

### 1.1 What We Have Now

**PromptGenerator (src/llm/prompt_generator.py)**:
- ✅ Jinja2 template-based system with YAML templates
- ✅ Token budget management and optimization
- ✅ Context prioritization and injection
- ✅ Custom filters for truncation, summarization, code formatting
- ✅ Template validation and caching
- ✅ Pattern learning integration (few-shot examples)
- ✅ Performance metrics tracking

**Prompt Templates (config/prompt_templates.yaml)**:
- ✅ task_execution template with structured sections
- ✅ validation template for quality control
- ✅ error_analysis, decision, code_review templates (via PRIORITY_BY_TEMPLATE)
- ✅ M9 features: dependency context, git integration, retry information
- ✅ JSON schema enforcement for validation responses
- ✅ Conditional sections based on available context

**Context Management (src/utils/context_manager.py)**:
- ✅ Template-specific priority orders (PRIORITY_BY_TEMPLATE)
- ✅ Template-specific scoring weights (WEIGHTS_BY_TEMPLATE)
- ✅ Token-aware context building
- ✅ Context summarization and compression

### 1.2 Where We Meet Requirements

✅ **Partial structured format**: Validation template enforces JSON responses
✅ **Context-based sections**: Templates have Context → Task → Instructions flow
✅ **Template variety**: Different templates for different use cases
✅ **Token optimization**: Automatic truncation and optimization
✅ **Code formatting**: format_code filter for consistent code presentation
✅ **Git integration**: Recent commits, branch info included in prompts
✅ **Dependency awareness**: Task dependencies shown in context
✅ **Retry context**: Previous failures and improvements noted

### 1.3 Critical Gaps Identified

❌ **Natural Language Dominance**: All prompts use human-readable text, not machine-optimized formats
❌ **No Response Format Enforcement**: Only validation template enforces JSON; task_execution uses free-form text
❌ **No Structured Prompt Rules System**: No formal rule engine for different prompt types
❌ **No Complexity Estimation**: Cannot predict task complexity or token requirements
❌ **No Task Decomposition Logic**: No automatic breakdown of complex tasks
❌ **No Parallel Agent Instructions**: No mechanism to instruct Claude to deploy multiple agents
❌ **Human-Centered Design**: Prompts formatted for human readability (sections, markdown, bullet points)
❌ **No LLM-to-LLM Protocol**: Obra and Claude communicate as if talking to humans
❌ **No Code Quality Rules**: No enforced rules for production-ready code, testing, documentation
❌ **No Documentation Strategy**: No distinction between LLM-optimized vs human-readable docs
❌ **No Graceful Parallel Agent Recovery**: No tracking of parallel agent attempts for recovery

---

## 2. Requirements Analysis

### 2.1 User Requirements (Enhanced with Best Practices)

#### REQUIREMENT 1: Universal Prompt Structure

**User Requirement**:
> "Prompts should be structured in a consistent format: 1) Context 2) Query/Command 3) Target response format or success criteria"

**Enhancement with Industry Best Practices**:
```
STANDARD PROMPT STRUCTURE (LLM-Optimized):
{
  "metadata": {
    "prompt_type": "task_execution | validation | error_analysis | decision | planning",
    "template_version": "1.0",
    "timestamp": "ISO-8601",
    "prompt_id": "unique_identifier",
    "token_budget": 100000,
    "response_format": "json | markdown | code"
  },
  "context": {
    "project": {...},
    "task": {...},
    "dependencies": [...],
    "history": {...},
    "constraints": {...}
  },
  "instruction": {
    "primary_objective": "string",
    "sub_objectives": [...],
    "success_criteria": [...],
    "failure_conditions": [...]
  },
  "response_schema": {
    "format": "json",
    "required_fields": [...],
    "optional_fields": [...],
    "validation_rules": {...}
  },
  "execution_constraints": {
    "max_tokens": 4096,
    "timeout_seconds": 300,
    "quality_thresholds": {...}
  }
}
```

**Rationale**:
- Structured JSON is more efficient for LLM parsing than natural language
- Machine-readable metadata enables automation and tracking
- Explicit response schema reduces parsing errors and rework
- Success criteria enables programmatic validation

**Current Gap**: We use natural language with markdown sections, not structured JSON

---

#### REQUIREMENT 2: Machine-Optimized Communication

**User Requirement**:
> "We should instruct Obra (Qwen) to send prompts to Claude in machine-optimized format (e.g., JSON). There's no need for Obra to use natural human language in prompts to Claude."

**Enhancement with Best Practices**:

**Best Practice Analysis**:
1. **Empirical Research** (OpenAI, Anthropic documentation):
   - JSON prompts can be 20-30% more token-efficient than prose
   - Structured prompts reduce ambiguity and parsing errors
   - LLMs excel at JSON generation and parsing

2. **However, Important Counterpoint**:
   - Claude Code CLI expects natural language prompts (human interface)
   - Claude models are *trained* on human conversations, not pure JSON
   - Some studies show natural language can provide better context for complex tasks
   - Hybrid approach may be optimal

**Recommended Hybrid Approach**:
```json
{
  "prompt_format": "structured_natural_language",
  "explanation": "Use JSON for metadata, structured data, and response schemas; use natural language for instructions and explanations",
  "example": {
    "metadata": {"type": "task_execution", "version": "1.0"},
    "context_data": {
      "task_id": 123,
      "dependencies": [121, 122],
      "retry_attempt": 2
    },
    "instruction_text": "Implement the user authentication module. Focus on security best practices including input validation, password hashing with bcrypt, and rate limiting. Previous attempt failed due to missing error handling - ensure all database operations have try-catch blocks.",
    "response_requirements": {
      "format": "json",
      "schema": {
        "status": "completed|failed|blocked",
        "files_modified": ["array of paths"],
        "tests_added": ["array of test names"],
        "issues_encountered": ["array of strings"]
      }
    }
  }
}
```

**Rationale**:
- Metadata and structured data in JSON for machine efficiency
- Complex instructions in natural language for clarity
- Response format strictly JSON for parsing reliability
- Best of both worlds: machine-readable structure with human-like instruction clarity

**Current Gap**: All prompts are pure natural language; no JSON structure

---

#### REQUIREMENT 3: Code Generation Rules

**User Requirement**:
> "Code should be written production-ready, no stubs, scalable, no hard-coded references, commented clearly for all functions, write tests as you go"

**Enhancement with Industry Best Practices**:

**CODE QUALITY RULESET**:
```yaml
code_generation_rules:
  quality_standards:
    - rule: "NO_STUBS"
      description: "All functions must have complete implementation"
      validation: "Reject if functions contain 'pass', 'TODO', or 'NotImplemented'"

    - rule: "NO_HARDCODED_VALUES"
      description: "No magic numbers or hardcoded paths/URLs"
      validation: "All configuration in constants or config files"
      examples:
        bad: "if port == 8080:"
        good: "if port == config.get('server.port', DEFAULT_PORT):"

    - rule: "PRODUCTION_SCALABILITY"
      description: "Code must handle production loads"
      requirements:
        - "Proper error handling for all I/O operations"
        - "Resource cleanup (files, connections, memory)"
        - "Logging for debugging (not print statements)"
        - "Connection pooling for databases"
        - "Rate limiting for APIs"
        - "Graceful degradation on failures"

    - rule: "COMPREHENSIVE_DOCUMENTATION"
      description: "All public interfaces must be documented"
      requirements:
        - "Docstrings for all public functions/classes (Google style)"
        - "Type hints for all function signatures"
        - "Inline comments for complex logic (not obvious code)"
        - "README.md for new modules"
        - "API documentation for new endpoints"

    - rule: "TEST_DRIVEN_DEVELOPMENT"
      description: "Tests must be written as code is developed"
      requirements:
        - "Unit tests for all public functions (≥80% coverage)"
        - "Integration tests for workflows"
        - "Edge case testing (empty inputs, large inputs, invalid inputs)"
        - "Mock external dependencies"
        - "Tests must pass before moving to next task"

    - rule: "CODE_STYLE_CONSISTENCY"
      description: "Follow project style guide"
      requirements:
        - "PEP 8 for Python (line length ≤100)"
        - "Consistent naming (snake_case for functions, PascalCase for classes)"
        - "No unused imports or variables"
        - "Black formatting for Python"
        - "Pylint score ≥9.0/10"

    - rule: "SECURITY_FIRST"
      description: "Security must be built-in, not bolted-on"
      requirements:
        - "Input validation for all user inputs"
        - "SQL injection prevention (parameterized queries)"
        - "XSS prevention (output escaping)"
        - "Secrets in environment variables, not code"
        - "Authentication/authorization checks"
        - "HTTPS for all external communications"
```

**Enforcement Strategy**:
1. **Pre-execution**: Include rules in prompt instruction section
2. **Post-execution**: QualityController validates against rules using AST analysis
3. **Iterative**: If rules violated, retry with specific violations noted
4. **Learning**: Track which rules are frequently violated for prompt optimization

**Current Gap**: No formal code quality rules; rely on general instructions

---

#### REQUIREMENT 4: Documentation Strategy

**User Requirement**:
> "Documentation for project management (task tracking, work breakdown, sequencing) should be LLM-optimized, human documentation should follow when major milestones are completed"

**Enhancement with Best Practices**:

**DOCUMENTATION TAXONOMY**:

```yaml
documentation_types:

  # Type 1: LLM-Optimized (Machine-Readable)
  llm_optimized:
    purpose: "Enable automated processing, parsing, and analysis"
    format: "JSON, YAML, or structured markdown with frontmatter"
    audience: "Other LLMs, automation scripts, Obra orchestrator"
    update_frequency: "Real-time (every task/subtask)"
    examples:
      - "Task dependency graphs (JSON)"
      - "Work breakdown structures (YAML)"
      - "Progress tracking (structured markdown)"
      - "Error logs (JSON with stack traces)"
      - "Performance metrics (JSON time series)"

    structure:
      task_tracking: |
        {
          "task_id": 123,
          "status": "in_progress",
          "dependencies": [121, 122],
          "blockers": [],
          "progress_percentage": 45,
          "subtasks": [
            {"id": "123.1", "status": "completed", "duration_ms": 45000},
            {"id": "123.2", "status": "in_progress", "estimated_remaining_ms": 120000}
          ],
          "metrics": {
            "files_modified": 3,
            "tests_added": 7,
            "lines_changed": {"+": 234, "-": 67}
          }
        }

      work_breakdown: |
        tasks:
          - id: "TASK_001"
            name: "Implement authentication module"
            complexity: "medium"
            estimated_tokens: 15000
            parallelizable: false
            subtasks:
              - id: "TASK_001.1"
                name: "Create User model"
                complexity: "low"
                estimated_tokens: 3000
                dependencies: []
                parallelizable: true
              - id: "TASK_001.2"
                name: "Implement password hashing"
                complexity: "low"
                estimated_tokens: 2000
                dependencies: ["TASK_001.1"]
                parallelizable: true

  # Type 2: Human-Readable (Communication)
  human_readable:
    purpose: "Communicate with human developers and stakeholders"
    format: "Markdown, HTML, or PDF with formatting"
    audience: "Developers, project managers, stakeholders"
    update_frequency: "Milestone completion (weekly/monthly)"
    examples:
      - "Release notes"
      - "Architecture documentation"
      - "User guides"
      - "API reference"
      - "Troubleshooting guides"

    trigger_conditions:
      - "Milestone completion (e.g., M0-M8)"
      - "Major version release"
      - "Architecture changes"
      - "External API changes"
      - "Critical bug fixes"

    generation_workflow:
      1_collect_llm_docs: "Aggregate all LLM-optimized docs for milestone"
      2_synthesize: "Use Qwen to synthesize human-readable summary"
      3_format: "Apply human-friendly formatting (headings, bullets, diagrams)"
      4_review: "Optional human review before publishing"

  # Type 3: Code Documentation (Both)
  code_documentation:
    purpose: "Explain code functionality for developers and LLMs"
    format: "Docstrings (Google style), inline comments, type hints"
    audience: "Both humans and LLMs"
    update_frequency: "Real-time (with code changes)"
    requirements:
      - "Machine-readable: Type hints, structured docstrings"
      - "Human-readable: Clear explanations, examples"
      - "Both: Accurate, up-to-date, concise"
```

**Implementation Strategy**:
- **Automatic LLM Doc Generation**: Every task completion triggers LLM-optimized doc update
- **Lazy Human Doc Generation**: Human docs generated only at milestones or on-demand
- **Dual-Purpose Code Docs**: Docstrings serve both audiences (type hints for machines, explanations for humans)

**Current Gap**: No distinction between LLM and human documentation types

---

#### REQUIREMENT 5: Task Planning & Complexity Estimation

**User Requirement**:
> "Work should be broken down into discrete independent segments, if work takes more than (X) then re-plan and break down further, optimize for parallelization"

**Enhancement with Best Practices**:

**TASK DECOMPOSITION FRAMEWORK**:

```yaml
complexity_estimation:

  # Estimation Heuristics (Empirical)
  heuristics:
    lines_of_code:
      simple: "≤100 LOC = ~1000-3000 tokens"
      medium: "100-500 LOC = ~3000-15000 tokens"
      complex: "500-2000 LOC = ~15000-60000 tokens"
      very_complex: ">2000 LOC = >60000 tokens (must decompose)"

    file_count:
      simple: "1-2 files"
      medium: "3-5 files"
      complex: "6-10 files"
      very_complex: ">10 files (must decompose)"

    dependency_depth:
      simple: "0-1 dependencies"
      medium: "2-3 dependencies"
      complex: "4-5 dependencies"
      very_complex: ">5 dependencies (must decompose)"

    conceptual_complexity:
      simple: "Single well-defined task (CRUD operation)"
      medium: "Multiple related tasks (auth module)"
      complex: "Cross-cutting concerns (logging system)"
      very_complex: "Architecture changes (plugin system)"

  # Decomposition Thresholds
  thresholds:
    max_estimated_tokens: 20000  # If task > 20K tokens, decompose
    max_files_per_task: 8
    max_dependencies_per_task: 4
    max_duration_minutes: 30  # Based on empirical Claude Code session data

  # Decomposition Algorithm
  decomposition_strategy:
    1_analyze_scope:
      - "Parse task description for verbs and nouns"
      - "Identify distinct capabilities required"
      - "Estimate LOC, files, dependencies"

    2_estimate_complexity:
      - "Calculate weighted complexity score"
      - "Compare against thresholds"
      - "If exceeds threshold → decompose"

    3_identify_subtasks:
      - "Break by functional boundaries (models, views, controllers)"
      - "Break by data flow (input → processing → output)"
      - "Break by dependencies (create User → create Auth → create Session)"

    4_analyze_dependencies:
      - "Build dependency graph"
      - "Identify critical path (must be sequential)"
      - "Identify parallelizable tasks (no shared state)"

    5_optimize_parallelization:
      - "Group independent tasks for parallel execution"
      - "Ensure parallel tasks have ≤2 dependencies each"
      - "Estimate parallel speedup"

  # Parallelization Rules
  parallelization:
    when_to_parallelize:
      - "≥2 independent subtasks identified"
      - "Each subtask complexity ≤ 'medium'"
      - "No shared mutable state between subtasks"
      - "Each subtask can be validated independently"

    parallel_agent_protocol:
      instruction_template: |
        {
          "parallel_execution": {
            "enabled": true,
            "tasks": [
              {
                "task_id": "SUBTASK_001",
                "agent_id": "agent_1",
                "dependencies": [],
                "timeout_seconds": 600
              },
              {
                "task_id": "SUBTASK_002",
                "agent_id": "agent_2",
                "dependencies": [],
                "timeout_seconds": 600
              }
            ],
            "coordination": {
              "merge_strategy": "sequential_validation",
              "conflict_resolution": "manual_review"
            },
            "failure_handling": {
              "retry_parallel": false,
              "fallback_to_sequential": true,
              "log_attempt": true
            }
          }
        }

      recovery_on_failure:
        - "Log parallel attempt with task_ids and failure reason"
        - "On retry, use sequential execution (fallback_to_sequential: true)"
        - "Update task metadata: parallel_attempted=true, parallel_failed=true"
```

**Complexity Estimation Example**:
```python
def estimate_task_complexity(task_description: str, context: Dict) -> Dict:
    """
    Estimate task complexity using heuristics.

    Returns:
        {
            'estimated_tokens': int,
            'estimated_loc': int,
            'estimated_files': int,
            'complexity_score': float,  # 0-100
            'should_decompose': bool,
            'recommended_subtasks': int
        }
    """
    # Use Qwen to analyze task description
    # Apply heuristics based on keywords, verb count, noun complexity
    # Return structured estimate
```

**Current Gap**: No complexity estimation or automatic task decomposition

---

### 2.2 Additional Domain Requirements (Proposed)

Beyond the user's specified domains, these additional areas need rules:

#### DOMAIN 6: Error Handling & Recovery

```yaml
error_handling_rules:

  prompt_instructions:
    - "Anticipate failure modes for all external dependencies"
    - "Implement circuit breakers for flaky services"
    - "Provide detailed error messages with context"
    - "Log errors with structured data (JSON) for analysis"
    - "Never swallow exceptions silently"

  response_requirements:
    error_report_schema:
      error_type: "string (exception class name)"
      error_message: "string (human-readable)"
      stack_trace: "string (full traceback)"
      context: "dict (relevant variables, state)"
      recovery_attempted: "bool"
      recovery_successful: "bool"
      user_action_required: "bool"
      suggested_fixes: "array of strings"

  retry_strategy:
    - "Exponential backoff for transient errors"
    - "Circuit breaker for persistent failures"
    - "Different retry logic for different error types"
    - "Maximum retry attempts to prevent infinite loops"
```

#### DOMAIN 7: Testing Strategy

```yaml
testing_rules:

  test_categories:
    unit_tests:
      - "Test each function in isolation"
      - "Mock all external dependencies"
      - "Cover edge cases (empty, null, large inputs)"
      - "Aim for ≥80% code coverage"

    integration_tests:
      - "Test workflows end-to-end"
      - "Use test database (not production)"
      - "Clean up resources after each test"
      - "Test failure scenarios"

    performance_tests:
      - "Test under expected load"
      - "Identify bottlenecks"
      - "Set performance baselines"

  test_naming_convention:
    pattern: "test_<function>_<scenario>_<expected_outcome>"
    examples:
      - "test_authenticate_valid_credentials_returns_token"
      - "test_authenticate_invalid_credentials_raises_exception"
      - "test_authenticate_missing_user_returns_none"

  test_organization:
    - "Mirror source code structure in tests/"
    - "One test file per source file"
    - "Group tests by class using test classes"
    - "Use fixtures for common setup"

  # CRITICAL: Parallel Agent Testing Protocol
  parallel_agent_testing_rules:
    rule_1_sequential_code_test:
      description: "NEVER write code and run tests in parallel"
      rationale: "Test execution can crash sessions; parallel crashes cause data loss"
      enforcement: "Code writing and test execution must be separate sequential tasks"

    rule_2_document_test_intentions:
      description: "Document test plan BEFORE executing tests"
      format: "Create test_plan.json with expected tests, coverage targets, pass criteria"
      location: "/tmp/test_intentions_<task_id>.json"
      rationale: "Durable record enables recovery if test crashes session"
      schema: |
        {
          "task_id": "string",
          "test_suite": "string (path to test file/directory)",
          "expected_tests": ["array of test names"],
          "coverage_target": "float (0.0-1.0)",
          "pass_criteria": "string (e.g., 'all tests pass')",
          "timeout_seconds": "int",
          "crash_recovery_plan": "string (what to do if session crashes)"
        }

    rule_3_test_as_discrete_event:
      description: "Testing is a distinct phase, not mixed with coding"
      workflow: |
        1. Code writing phase (Agent 1 or Agent 2)
        2. Document test intentions (/tmp/test_intentions_*.json)
        3. Commit code changes
        4. Testing phase (separate task, single agent)
        5. If tests fail, return to step 1
        6. If tests pass, mark task complete

    rule_4_single_agent_testing:
      description: "Only ONE agent runs tests at a time"
      rationale: "Concurrent test execution causes resource conflicts"
      enforcement: "Test tasks must have no parallel siblings"

    rule_5_test_crash_recovery:
      description: "If test crashes session, resume from test_intentions file"
      recovery_workflow: |
        1. Check for /tmp/test_intentions_*.json files
        2. If found, parse test plan
        3. Determine if tests were running (check timestamps)
        4. If crash during test, mark tests as "crashed"
        5. Report crash to orchestrator
        6. Orchestrator decides: retry tests or mark task as blocked

  test_execution_safety:
    max_test_duration: "300 seconds (5 minutes)"
    timeout_enforcement: "pytest --timeout=300"
    resource_limits: "Set pytest max workers to avoid WSL2 crashes"
    crash_detection: "Monitor for WSL2 kernel panics, session terminations"
```

#### DOMAIN 8: Performance & Optimization

```yaml
performance_rules:

  benchmarking:
    - "Profile before optimizing (no premature optimization)"
    - "Set performance baselines for critical paths"
    - "Monitor token usage per operation"
    - "Track LLM inference latency"
    - "Measure database query times"

  optimization_guidelines:
    - "Cache frequently accessed data"
    - "Use database indexes for common queries"
    - "Batch operations when possible"
    - "Async I/O for concurrent operations"
    - "Lazy loading for expensive resources"

  resource_management:
    - "Set memory limits for LLM context windows"
    - "Implement pagination for large datasets"
    - "Stream large responses instead of buffering"
    - "Close connections and file handles properly"
```

#### DOMAIN 9: Security & Privacy

```yaml
security_rules:

  input_validation:
    - "Validate all user inputs against schema"
    - "Sanitize inputs to prevent injection attacks"
    - "Use allow-lists, not deny-lists"
    - "Enforce length limits on all string inputs"

  data_protection:
    - "Encrypt sensitive data at rest"
    - "Use HTTPS for data in transit"
    - "Never log passwords or API keys"
    - "Implement proper access control"

  secrets_management:
    - "Store secrets in environment variables or secret managers"
    - "Never commit secrets to version control"
    - "Rotate secrets regularly"
    - "Use different secrets for dev/staging/production"
```

---

## 3. LLM-First Design Principles

### 3.1 Human-Centered Decisions to Revisit

**Current Human-Centered Designs**:

1. **Markdown Formatting** (src/llm/prompt_generator.py, prompt_templates.yaml)
   - **Issue**: Markdown is for human readability, wastes tokens on formatting
   - **LLM-First Alternative**: Structured JSON with clear hierarchy

2. **Natural Language Section Headers** (prompt_templates.yaml)
   - **Issue**: "## Task Information", "## Recent Errors" are human-friendly but verbose
   - **LLM-First Alternative**: JSON keys: `"task_info"`, `"recent_errors"`

3. **Bullet Point Lists** (prompt_templates.yaml)
   - **Issue**: "- Item 1\n- Item 2" uses tokens for formatting
   - **LLM-First Alternative**: JSON arrays: `["Item 1", "Item 2"]`

4. **Explanatory Text** (prompt_templates.yaml: "You are working on...", "Please complete this task efficiently...")
   - **Issue**: Polite preambles waste tokens
   - **LLM-First Alternative**: Direct instruction object: `{"instruction": "complete_task", "details": {...}}`

5. **Human-Readable Timestamps** (prompt_templates.yaml: "{{ commit.timestamp }}")
   - **Issue**: Verbose formatted dates
   - **LLM-First Alternative**: ISO-8601 or Unix timestamps

6. **Emoji Usage** (prompt_templates.yaml: "🔄 Retry Information", "⚠️ Blocking")
   - **Issue**: Emojis are multi-byte characters, unclear meaning for LLMs
   - **LLM-First Alternative**: JSON flags: `"is_retry": true`, `"is_blocking": true`

7. **Free-Form Text Responses** (task_execution template)
   - **Issue**: Claude can respond in any format, making parsing unreliable
   - **LLM-First Alternative**: Enforce JSON response schema for all prompts

### 3.2 Proposed LLM-Optimized Redesign

**Example: Current task_execution Template (Human-Centered)**:
```jinja2
You are working on the following task for the "{{ project_name }}" project.

## Task Information
**Task ID**: {{ task_id }}
**Title**: {{ task_title }}
**Description**: {{ task_description }}

## Instructions
{{ instructions }}

Please complete this task efficiently and report your progress.
```

**Token Count**: ~150-200 tokens (with typical values)

**Redesigned: LLM-Optimized Version**:
```json
{
  "v": "1.0",
  "type": "task_exec",
  "proj": {
    "name": "{{project_name}}",
    "dir": "{{working_directory}}"
  },
  "task": {
    "id": {{task_id}},
    "title": "{{task_title}}",
    "desc": "{{task_description}}",
    "priority": {{task_priority}},
    "deps": {{task_dependencies | tojson}}
  },
  "instr": "{{instructions}}",
  "resp_fmt": {
    "type": "json",
    "schema": {
      "status": "enum[completed,failed,blocked]",
      "files": ["array"],
      "tests": ["array"],
      "issues": ["array"]
    }
  }
}
```

**Token Count**: ~80-100 tokens (with typical values)
**Savings**: ~40-50% token reduction

**Trade-off Analysis**:
- ✅ **Pros**: More efficient, parseable, standardized
- ❌ **Cons**: Less readable for humans debugging prompts
- ⚖️ **Mitigation**: Provide human-readable preview mode for debugging

---

## 4. Architecture Proposal

### 4.1 Prompt Rule Engine

**Component**: `PromptRuleEngine`
**Location**: `src/llm/prompt_rule_engine.py`
**Purpose**: Apply domain-specific rules to prompts and responses

```python
class PromptRuleEngine:
    """
    Applies domain-specific rules to prompts and validates responses.

    Features:
    - Load rules from YAML configuration
    - Apply rules based on prompt type
    - Validate responses against rules
    - Track rule violations for learning
    """

    def __init__(self, rules_config_path: str):
        """Load rules from YAML configuration."""

    def get_rules_for_prompt_type(
        self,
        prompt_type: str
    ) -> List[PromptRule]:
        """Get applicable rules for a prompt type."""

    def apply_rules_to_prompt(
        self,
        prompt: Dict[str, Any],
        prompt_type: str
    ) -> Dict[str, Any]:
        """Inject rules into prompt instruction section."""

    def validate_response_against_rules(
        self,
        response: Dict[str, Any],
        prompt_type: str
    ) -> RuleValidationResult:
        """Validate response adheres to rules."""

    def log_rule_violation(
        self,
        rule_id: str,
        violation_details: Dict
    ):
        """Track violations for analysis and learning."""
```

**Rules Configuration** (`config/prompt_rules.yaml`):
```yaml
prompt_rules:

  code_generation:
    - id: "CODE_001"
      name: "NO_STUBS"
      description: "All functions must have complete implementation"
      validation_type: "ast_analysis"
      validation_code: |
        def validate(code_ast):
            # Check for 'pass', 'TODO', 'NotImplemented'
            return has_complete_implementation(code_ast)
      severity: "error"
      auto_fix: false

    - id: "CODE_002"
      name: "COMPREHENSIVE_TESTS"
      description: "Tests must be written for all new functions"
      validation_type: "coverage_check"
      validation_code: |
        def validate(files_changed, test_files):
            return all(has_corresponding_test(f) for f in files_changed)
      severity: "error"
      auto_fix: false

  documentation:
    - id: "DOC_001"
      name: "LLM_OPTIMIZED_FORMAT"
      description: "Task tracking docs must be JSON or YAML"
      validation_type: "format_check"
      validation_code: |
        def validate(doc_path):
            return doc_path.endswith(('.json', '.yaml', '.yml'))
      severity: "warning"
      auto_fix: false
```

### 4.2 Structured Prompt Builder

**Component**: `StructuredPromptBuilder`
**Location**: `src/llm/structured_prompt_builder.py`
**Purpose**: Build machine-optimized structured prompts

```python
class StructuredPromptBuilder:
    """
    Build machine-optimized prompts in JSON format.

    Integrates with existing PromptGenerator for backward compatibility.
    """

    def __init__(
        self,
        rule_engine: PromptRuleEngine,
        context_manager: ContextManager,
        token_counter: TokenCounter
    ):
        """Initialize with rule engine and context manager."""

    def build_prompt(
        self,
        prompt_type: str,
        context: Dict[str, Any],
        instruction: str,
        response_schema: Dict[str, Any],
        max_tokens: int = 100000
    ) -> Dict[str, Any]:
        """
        Build structured prompt.

        Returns JSON-formatted prompt ready for LLM.
        """
        # 1. Apply rules
        applicable_rules = self.rule_engine.get_rules_for_prompt_type(prompt_type)

        # 2. Build context with template-specific prioritization
        prioritized_context = self.context_manager.build_context(
            context_items,
            max_tokens=max_tokens - 5000,  # Reserve space for instruction
            template_name=prompt_type
        )

        # 3. Build structured prompt
        prompt = {
            "metadata": {
                "prompt_type": prompt_type,
                "version": "1.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "prompt_id": generate_prompt_id(),
                "token_budget": max_tokens
            },
            "context": prioritized_context,
            "instruction": {
                "primary": instruction,
                "rules": [rule.to_dict() for rule in applicable_rules]
            },
            "response_schema": response_schema
        }

        # 4. Optimize for token budget
        return self._optimize_prompt_tokens(prompt, max_tokens)

    def _optimize_prompt_tokens(
        self,
        prompt: Dict,
        max_tokens: int
    ) -> Dict:
        """Optimize structured prompt to fit token budget."""
        # Use JSON minification, abbreviate keys, truncate context
```

### 4.3 Response Parser

**Component**: `StructuredResponseParser`
**Location**: `src/llm/structured_response_parser.py`
**Purpose**: Parse and validate structured LLM responses

```python
class StructuredResponseParser:
    """
    Parse structured responses from LLMs.

    Features:
    - JSON extraction from various formats
    - Schema validation
    - Default value injection
    - Error recovery
    """

    def __init__(self, rule_engine: PromptRuleEngine):
        """Initialize with rule engine for validation."""

    def parse_response(
        self,
        raw_response: str,
        expected_schema: Dict[str, Any],
        prompt_type: str
    ) -> ParsedResponse:
        """
        Parse and validate LLM response.

        Returns:
            ParsedResponse with:
            - is_valid: bool
            - data: Dict (parsed JSON)
            - errors: List[str] (validation errors)
            - rule_violations: List[RuleViolation]
        """
        # 1. Extract JSON (use existing json_extractor.py)
        json_data = extract_json(raw_response)

        # 2. Validate against schema
        is_valid, schema_errors = validate_json_structure(
            json_data,
            expected_schema['required_fields']
        )

        # 3. Validate against rules
        rule_result = self.rule_engine.validate_response_against_rules(
            json_data,
            prompt_type
        )

        # 4. Return parsed response
        return ParsedResponse(
            is_valid=is_valid and rule_result.is_valid,
            data=json_data,
            schema_errors=schema_errors,
            rule_violations=rule_result.violations
        )
```

### 4.4 Complexity Estimator

**Component**: `TaskComplexityEstimator`
**Location**: `src/orchestration/complexity_estimator.py`
**Purpose**: Estimate task complexity and recommend decomposition

```python
class TaskComplexityEstimator:
    """
    Estimate task complexity using heuristics and LLM analysis.

    Features:
    - Multi-factor complexity scoring
    - Decomposition recommendations
    - Parallelization analysis
    """

    def __init__(
        self,
        llm_interface: LocalLLMInterface,
        config: Dict[str, Any]
    ):
        """Initialize with LLM interface for analysis."""

    def estimate_complexity(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> ComplexityEstimate:
        """
        Estimate task complexity.

        Returns:
            ComplexityEstimate with:
            - estimated_tokens: int
            - estimated_loc: int
            - estimated_files: int
            - complexity_score: float (0-100)
            - should_decompose: bool
            - decomposition_suggestions: List[SubTask]
            - parallelization_opportunities: List[ParallelGroup]
        """
        # 1. Use heuristics (keyword analysis)
        heuristic_score = self._heuristic_analysis(task_description)

        # 2. Use LLM for detailed analysis
        llm_analysis = self._llm_analysis(task_description, context)

        # 3. Combine scores
        final_estimate = self._combine_estimates(heuristic_score, llm_analysis)

        # 4. Check decomposition thresholds
        if final_estimate.complexity_score > self.config['decomposition_threshold']:
            final_estimate.should_decompose = True
            final_estimate.decomposition_suggestions = self._suggest_decomposition(
                task_description,
                context
            )

        return final_estimate
```

### 4.5 Integration with Existing Architecture

**Integration Points**:

1. **Orchestrator** (`src/orchestrator.py`)
   - Use `TaskComplexityEstimator` before executing task
   - If complexity too high, trigger automatic decomposition
   - If parallelization identified, deploy multiple Claude Code agents

2. **PromptGenerator** (`src/llm/prompt_generator.py`)
   - Add `structured_mode: bool` parameter
   - If `structured_mode=True`, delegate to `StructuredPromptBuilder`
   - If `structured_mode=False`, use existing Jinja2 templates (backward compatibility)

3. **QualityController** (`src/orchestration/quality_controller.py`)
   - Use `StructuredResponseParser` to parse responses
   - Validate against `PromptRuleEngine` rules
   - Track rule violations for learning

4. **StateManager** (`src/core/state.py`)
   - Add `parallel_agent_attempts` table for tracking
   - Log complexity estimates for analysis
   - Store rule violations for continuous improvement

**Backward Compatibility**:
- Keep existing Jinja2 templates and natural language prompts
- Add `structured_mode` flag to gradually migrate
- Support hybrid mode (JSON metadata + natural language instructions)
- Provide migration path for existing code

---

## 5. Implementation Considerations

### 5.1 Performance Impact

**Token Efficiency**:
- Structured prompts: 30-50% token reduction (estimated)
- Faster parsing: JSON vs text parsing is 5-10x faster
- Reduced retry loops: Structured responses easier to validate

**Processing Overhead**:
- JSON serialization/deserialization: ~1-5ms per prompt/response
- Rule validation: ~10-50ms depending on rule complexity
- AST analysis for code rules: ~50-200ms per file

**Net Impact**: Positive (token savings outweigh processing overhead)

### 5.2 Testing Strategy

**Unit Tests**:
- Test each component in isolation
- Mock LLM responses for predictable testing
- Test rule application and validation logic
- Test complexity estimation accuracy

**Integration Tests**:
- Test end-to-end prompt generation → LLM → response parsing
- Test parallel agent deployment and recovery
- Test automatic task decomposition
- Test rule violation tracking and learning

**Validation Tests**:
- Compare structured vs natural language prompts for same task
- Measure token usage, latency, success rate
- A/B testing with real Claude Code sessions

### 5.3 Migration Path

**Phase 1: Add Infrastructure** (1-2 weeks)
- Implement PromptRuleEngine, StructuredPromptBuilder, StructuredResponseParser
- Add configuration files (prompt_rules.yaml)
- Write comprehensive tests

**Phase 2: Hybrid Mode** (1-2 weeks)
- Add `structured_mode` flag to Orchestrator
- Support both modes in parallel
- Collect metrics on both approaches

**Phase 3: Gradual Migration** (2-4 weeks)
- Migrate validation prompts to structured format first (already JSON responses)
- Migrate task_execution prompts to hybrid format (JSON metadata + NL instructions)
- Migrate error_analysis and decision prompts

**Phase 4: Full LLM-Optimized** (2-4 weeks)
- Default to structured mode
- Deprecate pure natural language mode
- Optimize based on collected metrics

---

## 6. Response Schema Specifications

### 6.1 Task Execution Response

```json
{
  "response_schema": {
    "type": "object",
    "required_fields": [
      "status",
      "files_modified",
      "tests_added",
      "execution_summary"
    ],
    "optional_fields": [
      "issues_encountered",
      "suggestions",
      "complexity_increase",
      "parallel_tasks_identified"
    ],
    "field_definitions": {
      "status": {
        "type": "enum",
        "values": ["completed", "failed", "blocked", "needs_decomposition"]
      },
      "files_modified": {
        "type": "array",
        "items": {
          "path": "string",
          "change_type": "enum[created,modified,deleted]",
          "lines_changed": {"added": "int", "removed": "int"}
        }
      },
      "tests_added": {
        "type": "array",
        "items": {
          "test_file": "string",
          "test_name": "string",
          "coverage_percentage": "float"
        }
      },
      "execution_summary": {
        "type": "string",
        "max_length": 500,
        "description": "Brief summary of work completed"
      },
      "issues_encountered": {
        "type": "array",
        "items": {
          "issue_type": "enum[error,warning,blocker]",
          "description": "string",
          "resolution": "string or null"
        }
      },
      "parallel_tasks_identified": {
        "type": "array",
        "items": {
          "task_description": "string",
          "estimated_complexity": "enum[low,medium,high]",
          "dependencies": ["array of task IDs"]
        }
      }
    }
  }
}
```

### 6.2 Validation Response

(Already implemented in TASK_1.2, but included for completeness)

```json
{
  "response_schema": {
    "type": "object",
    "required_fields": [
      "is_valid",
      "quality_score",
      "issues",
      "suggestions"
    ],
    "optional_fields": [
      "dependency_concerns",
      "reasoning"
    ],
    "field_definitions": {
      "is_valid": {
        "type": "boolean",
        "description": "Whether work meets acceptance criteria"
      },
      "quality_score": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "description": "Overall quality rating"
      },
      "issues": {
        "type": "array",
        "items": "string",
        "description": "List of problems found"
      },
      "suggestions": {
        "type": "array",
        "items": "string",
        "description": "Recommended improvements"
      },
      "dependency_concerns": {
        "type": "array",
        "items": "string",
        "description": "Potential issues with downstream tasks"
      }
    }
  }
}
```

---

## 7. Key Recommendations

### 7.1 Immediate Actions

1. **Implement Hybrid Approach First**
   - JSON for metadata and structured data
   - Natural language for complex instructions
   - Best balance between efficiency and clarity

2. **Start with Validation Prompts**
   - Already use JSON responses
   - Easy migration to structured prompts
   - Low risk, high learning value

3. **Build Complexity Estimator**
   - Critical for automatic task decomposition
   - Enables intelligent parallelization
   - High impact on overall efficiency

4. **Create Prompt Rules YAML**
   - Centralized rule configuration
   - Easier to update and tune rules
   - Enables rule learning and optimization

### 7.2 Long-Term Strategic Improvements

1. **Continuous Rule Learning**
   - Track rule violations over time
   - Use parameter effectiveness tracking (TASK_2.1) for rules
   - Automatically adjust rules based on success/failure data

2. **A/B Testing Framework**
   - Compare structured vs natural language prompts
   - Measure token efficiency, success rate, latency
   - Data-driven decisions on format adoption

3. **Parallel Agent Orchestration**
   - Build robust parallel agent deployment system
   - Implement conflict resolution and merge strategies
   - Track parallel successes/failures for learning

4. **LLM-First Documentation Pipeline**
   - Automatic LLM-optimized doc generation
   - On-demand human-readable synthesis
   - Version control for both doc types

### 7.3 Metrics to Track

**Efficiency Metrics**:
- Average tokens per prompt (structured vs natural language)
- Parsing success rate (JSON extraction)
- Response validation pass rate
- Token utilization efficiency (useful tokens / total tokens)

**Quality Metrics**:
- Rule violation rate by rule type
- Task success rate by complexity level
- Parallel agent success vs failure rate
- Decomposition accuracy (were subtasks right?)

**Learning Metrics**:
- Rule effectiveness over time
- Complexity estimation accuracy
- Parameter effectiveness (already tracking in TASK_2.1)
- Parallelization speedup achieved

---

## 8. Conclusion

This design proposes a comprehensive LLM-first prompt engineering framework that:

✅ **Standardizes prompts** with universal structure (metadata, context, instruction, response schema)
✅ **Optimizes for machine communication** with hybrid JSON + natural language approach
✅ **Enforces quality rules** for code, documentation, testing across all domains
✅ **Enables intelligent task breakdown** with complexity estimation and automatic decomposition
✅ **Supports parallelization** with robust parallel agent deployment and recovery
✅ **Maintains backward compatibility** with gradual migration path
✅ **Focuses on LLM-first design** while preserving human debuggability

**Next Steps**:
1. Review this design document
2. Gather feedback and adjust approach
3. Develop detailed implementation plan (separate document)
4. Begin Phase 1 implementation (infrastructure components)

---

## Appendix A: Example Prompts

### A.1 Structured Task Execution Prompt (Hybrid)

```json
{
  "metadata": {
    "type": "task_execution",
    "version": "1.0",
    "timestamp": "2025-11-03T14:30:00Z",
    "prompt_id": "task_exec_123_001",
    "token_budget": 100000
  },
  "context": {
    "project": {
      "name": "obra",
      "directory": "/home/user/obra",
      "goals": "Build autonomous LLM orchestration system"
    },
    "task": {
      "id": 123,
      "title": "Implement user authentication module",
      "priority": 8,
      "dependencies": [121, 122],
      "estimated_complexity": "medium"
    },
    "dependencies_status": [
      {"id": 121, "title": "Create User model", "status": "completed"},
      {"id": 122, "title": "Setup database", "status": "completed"}
    ],
    "recent_errors": [],
    "git": {
      "branch": "feature/auth-module",
      "uncommitted_changes": 0,
      "recent_commits": [
        {"hash": "a3c4f21", "message": "Add User model", "author": "dev"}
      ]
    }
  },
  "instruction": {
    "primary": "Implement the user authentication module including password hashing, token generation, and session management. Focus on security best practices including input validation, rate limiting, and secure password storage.",
    "rules": [
      {
        "id": "CODE_001",
        "name": "NO_STUBS",
        "description": "All functions must have complete implementation"
      },
      {
        "id": "CODE_002",
        "name": "COMPREHENSIVE_TESTS",
        "description": "Write unit tests for all public functions"
      },
      {
        "id": "CODE_004",
        "name": "PRODUCTION_SCALABILITY",
        "description": "Implement proper error handling and resource cleanup"
      },
      {
        "id": "SEC_001",
        "name": "INPUT_VALIDATION",
        "description": "Validate all user inputs against schema"
      }
    ],
    "success_criteria": [
      "All authentication endpoints implemented and working",
      "Password hashing uses bcrypt with proper salt",
      "Token generation uses secure random generation",
      "Rate limiting implemented for login attempts",
      "Unit tests with ≥80% coverage",
      "Integration tests for login/logout flow"
    ]
  },
  "response_schema": {
    "format": "json",
    "required_fields": [
      "status",
      "files_modified",
      "tests_added",
      "execution_summary"
    ],
    "field_definitions": {
      "status": {"type": "enum", "values": ["completed", "failed", "blocked"]},
      "files_modified": {
        "type": "array",
        "items": {"path": "string", "change_type": "string", "lines_changed": "object"}
      },
      "tests_added": {
        "type": "array",
        "items": {"test_file": "string", "test_name": "string"}
      },
      "execution_summary": {"type": "string", "max_length": 500}
    }
  }
}
```

### A.2 Structured Response Example

```json
{
  "status": "completed",
  "files_modified": [
    {
      "path": "src/auth/authentication.py",
      "change_type": "created",
      "lines_changed": {"added": 234, "removed": 0}
    },
    {
      "path": "src/auth/token_manager.py",
      "change_type": "created",
      "lines_changed": {"added": 127, "removed": 0}
    },
    {
      "path": "src/api/auth_endpoints.py",
      "change_type": "modified",
      "lines_changed": {"added": 98, "removed": 12}
    }
  ],
  "tests_added": [
    {
      "test_file": "tests/test_authentication.py",
      "test_name": "test_login_valid_credentials",
      "coverage_percentage": 85.4
    },
    {
      "test_file": "tests/test_authentication.py",
      "test_name": "test_login_invalid_credentials",
      "coverage_percentage": 85.4
    },
    {
      "test_file": "tests/test_token_manager.py",
      "test_name": "test_generate_token_valid_user",
      "coverage_percentage": 92.1
    }
  ],
  "execution_summary": "Implemented authentication module with bcrypt password hashing, JWT token generation, and Redis-based session management. Added rate limiting (5 attempts per minute) and comprehensive input validation. All 12 unit tests passing with 87% overall coverage.",
  "issues_encountered": [],
  "rule_compliance": {
    "CODE_001": {"compliant": true},
    "CODE_002": {"compliant": true},
    "CODE_004": {"compliant": true},
    "SEC_001": {"compliant": true}
  }
}
```

---

**End of Design Document**
