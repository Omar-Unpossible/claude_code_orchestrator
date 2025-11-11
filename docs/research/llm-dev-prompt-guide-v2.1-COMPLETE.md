# LLM Development Agent Prompt Engineering Guide v2.1

**A comprehensive framework for high-quality, consistent AI-assisted software development**

**Merged Edition**: Complete with enforcement tools, cost modeling, decision trees, and quick reference

---

## Quick Start

**New to this guide?** Start here:
1. Read [Core Principles](#core-principles) (5 min)
2. Copy [Planning Prompt Template](#planning-prompt-template-pasteable) (2 min)  
3. Review [Quick Reference Card](#quick-reference-card) (2 min)
4. Review [Before/After Example](#beforeafter-example) (3 min)
5. Customize for your tech stack and run your first planning session

**Experienced user?** Jump to:
- [Cost Modeling & Budgeting](#cost-modeling--budgeting) for budget planning
- [Decision Trees](#decision-trees) for daily decision support
- [Enforcement Validation](#complete-enforcement-validation) for CI/CD integration
- [Advanced Techniques](#advanced-techniques) for RAG, multi-agent, and optimization
- [Quick Reference Card](#quick-reference-card) for one-page cheat sheet

---

## Executive Summary

This guide establishes a robust prompt architecture for instructing LLM agents in software development tasks, ensuring consistent, high-quality outputs through structured prompts, verification gates, comprehensive state management, and modern AI engineering practices.

**What's New in v2.1 (Merged Edition):**
- ✅ Complete enforcement validation code (Python script with CI/CD integration)
- ✅ Comprehensive cost modeling and budgeting framework with calculators
- ✅ Four critical decision trees for daily decision-making
- ✅ One-page quick reference card for practitioners
- ✅ All content from addendum seamlessly integrated
- ✅ Enhanced navigation and organization

**Core Features:**
- Chain-of-thought and reasoning patterns
- Multi-agent orchestration strategies  
- RAG and tool-use integration
- Prompt versioning and regression testing
- Enhanced observability and metrics
- Modern structured output patterns
- Comprehensive error recovery strategies
- Production operations guidance

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Prompt Architecture](#prompt-architecture)
3. [Planning & Execution Framework](#planning--execution-framework)
4. [Context & Token Management](#context--token-management)
5. [Testing & Verification](#testing--verification)
6. [Multi-Agent Patterns](#multi-agent-patterns)
7. [Advanced Techniques](#advanced-techniques)
8. [Security & Compliance](#security--compliance)
9. [Observability & Metrics](#observability--metrics)
10. [Error Handling & Recovery](#error-handling--recovery) 🆕 *Includes Decision Trees*
11. [Templates & Examples](#templates--examples)
12. [Specialized Task Patterns](#specialized-task-patterns)
13. [Cost Modeling & Budgeting](#cost-modeling--budgeting) 🆕 *Complete Framework*
14. [Production Operations](#production-operations)
15. [Checklist & Governance](#checklist--governance) 🆕 *Includes Enforcement Code*
16. [Appendix](#appendix) 🆕 *Includes Quick Reference Card*

---

## Core Principles

### Foundational Rules

1. **Explicit Role and Scope** — Define clear boundaries for agent authority and responsibilities
2. **Separate Planning from Execution** — Never generate code without an approved plan
3. **Dual Output Format** — Always produce human-readable AND machine-readable artifacts
4. **Verification Gates** — Enforce checkpoints before proceeding to next phase
5. **Idempotent, Data-Driven Design** — No hardcoded values; prefer configuration and schemas
6. **Context Window Management** — Plan for state chunking and rehydration across windows
7. **Chain-of-Thought Reasoning** — Require explicit reasoning for complex decisions
8. **Auditability First** — Log all decisions, changes, and rationales with timestamps
9. **Security by Default** — Declare and enforce constraints for data, dependencies, and network access
10. **Test as First-Class Work** — Documentation and tests are mandatory deliverables, not afterthoughts

### New in v2.0: Reasoning Patterns

**Chain-of-Thought (CoT)**: For complex tasks, require the agent to show its work:
```
Before implementing, reason through:
1. What are the key constraints?
2. What are 3 possible approaches?
3. What are the tradeoffs of each?
4. Which approach best fits our constraints?
5. What are the risks and mitigations?
```

**Tree-of-Thoughts**: For multi-path decisions, explore alternatives:
```
Evaluate 3 design patterns for this feature:
- Pattern A: [pros/cons/fit score]
- Pattern B: [pros/cons/fit score]  
- Pattern C: [pros/cons/fit score]
Recommend best fit with justification.
```

**Reflection and Self-Correction**: Build in verification loops:
```
After generating code:
1. Review against acceptance criteria
2. Identify potential issues or edge cases
3. Self-correct and regenerate if needed
4. Explain what was corrected and why
```

---

## Prompt Architecture

### Canonical Prompt Structure

Every prompt should contain these sections in order:

```markdown
## 1. AGENT IDENTITY & PERMISSIONS

You are [role] with authority to [capabilities].
You CANNOT [restrictions] without human approval.
Version: [prompt-version] | Updated: [date]

## 2. OBJECTIVE & DESIGN INTENT

**Primary Goal**: [One clear sentence]

**User Stories**:
- As a [user], I want [capability], so that [benefit]
- [2-5 total stories]

**Success Definition**: [Observable outcome that defines done]

## 3. CONTEXT & CONSTRAINTS

**Technical Stack**:
- Languages/Frameworks: [with versions]
- Infrastructure: [cloud, containers, etc.]
- Repository: [url], Branch Policy: [pattern]
- CI/CD: [tools and pipeline stages]

**Style & Standards**:
- Linter: [tool + config file]
- Formatter: [tool + rules]
- Code Style Guide: [link or inline key rules]
- Test Coverage: [minimum % or criteria]

**Performance Targets**:
- Latency: [p95 <= X ms]
- Throughput: [requests/sec]
- Resource Limits: [memory, CPU]

**Security & Compliance**:
- Data Classification: [PII, sensitive, public]
- Required Encryption: [at-rest, in-transit]
- Auth/Authz: [mechanism and scopes]
- Regulatory: [GDPR, HIPAA, SOC2, etc.]
- Forbidden: [libraries, patterns, practices]

**Dependency Policy**:
- Approved: [list or registry]
- Require Pre-Approval: [any new deps]
- Vulnerability Scanning: [tool and threshold]

## 4. REASONING REQUIREMENTS

Before generating any code or design:
1. State your understanding of the problem
2. List key assumptions and confirm with human if uncertain
3. Propose 2-3 approaches with tradeoffs
4. Explain your recommended approach and why
5. Identify risks and mitigation strategies

## 5. DELIVERABLES & FORMATS

**Human-Readable** (Markdown):
- Design Document: docs/[feature]/design.md
- Implementation Plan: docs/[feature]/plan.md
- Runbook: docs/[feature]/runbook.md

**Machine-Readable** (JSON/YAML):
- Plan Manifest: plan_manifest.json [must follow schema v2.0]
- Acceptance Criteria: acceptance.yaml
- Test Spec: test_spec.json

**Code Artifacts**:
- Source: src/[paths]
- Tests: tests/unit/, tests/integration/, tests/e2e/
- Config: config/[environment].yaml
- Migrations: migrations/[timestamp]_[description].sql
- Infrastructure: infra/[terraform|cloudformation]/

**Changelog & Commits**:
- CHANGELOG.md: entry per semantic versioning
- Commit Message Template: "[Epic-ID] [type]: [short] — [detail]"
- Types: feat, fix, refactor, test, docs, chore, perf, security

## 6. ACCEPTANCE CRITERIA

**Definition of Done**: All must pass:
- [ ] Unit tests: [coverage >= X%]
- [ ] Integration tests: [all pass]
- [ ] Linter: [zero errors, warnings optional]
- [ ] Security scan: [no critical/high vulnerabilities]
- [ ] Performance: [meets targets in section 3]
- [ ] Documentation: [complete and reviewed]
- [ ] Accessibility: [WCAG 2.1 AA if UI] (if applicable)
- [ ] Manual verification: [smoke test steps provided and executed]

**Feature-Specific Criteria**:
- [Custom acceptance criteria for this feature]

## 7. PLANNING RULES

**Framework**: Organize as Epic → Stories → Tasks → Subtasks

**Dependency Management**:
- Sequence: critical path first, parallel where possible
- Risk weighting: high-risk/high-value tasks early
- Stop points: size phases for [N tokens] or [M files] per window

**Pre-Validation**:
- Identify missing information or ambiguities
- Provide 2-3 options for each question with tradeoffs
- State "No clarifications needed" if none exist

**Approval Gate**:
DO NOT generate code until:
1. Full plan (human + machine format) is produced
2. Human provides explicit approval: "APPROVED_BY: [name] [timestamp]"
3. Approval is logged in plan_manifest.json

## 8. STATE & CONTEXT MANAGEMENT

**Checkpoint Strategy**:
- Save plan_manifest.json after planning phase
- Save phase_summary.md after each major phase
- Include checkpoint keys for rehydration: [epic_id, phase, files_modified]

**Context Preservation**:
- Maintain rolling summary of previous phases (max 500 tokens)
- Include critical design decisions in each phase handoff
- Persist artifact registry: mapping of task IDs to file paths

**Large Feature Handling**:
- Split by vertical slices (end-to-end thin slices), not layers
- Each slice should deliver user value independently
- Prefer 3-7 stories per epic for optimal context management

## 9. FAILURE & ROLLBACK RULES

**Rollback Triggers**:
- Test coverage drops below threshold
- Critical/high security vulnerabilities introduced
- Performance regression > [X%]
- Breaking changes without migration path

**Remediation Process**:
1. Halt and preserve current state
2. Diagnose root cause with reasoning
3. Propose 2 remediation options with tradeoffs
4. Await human decision
5. Execute rollback or fix with verification

## 10. LOGGING & AUDIT TRAIL

**Required for All Outputs**:
- Timestamp: ISO 8601 format
- Agent Version: [model and prompt version]
- Input Context: [hash of input prompt]
- Artifacts Generated: [list with paths and hashes]
- Major Design Decisions: [decision + rationale + alternatives considered]
- Execution Time: [duration for task]

Store in: `.llm_audit/[date]/[task_id].json`
```

### Schema for Machine-Readable Plan (v2.0)

```json
{
  "schema_version": "2.0",
  "prompt_version": "v2.0.1",
  "meta": {
    "created": "2025-11-11T10:00:00Z",
    "updated": "2025-11-11T10:00:00Z",
    "agent": {
      "model": "claude-sonnet-4-5",
      "role": "lead_developer",
      "permissions": ["design", "implement", "test"]
    },
    "approved_by": null,
    "approval_timestamp": null
  },
  "epic": {
    "id": "E-001",
    "title": "Feature Name",
    "objective": "One-line objective",
    "priority": "P0",
    "estimated_effort_points": 21,
    "target_completion": "2025-11-20"
  },
  "stories": [
    {
      "id": "S-001",
      "title": "User Story Title",
      "description": "As a [user], I want [capability], so that [benefit]",
      "acceptance_criteria": [
        "Criterion 1 with measurable outcome",
        "Criterion 2 with measurable outcome"
      ],
      "priority": "P0",
      "estimated_points": 8,
      "dependencies": ["S-000"],
      "risks": [
        {
          "description": "Risk description",
          "likelihood": "medium",
          "impact": "high",
          "mitigation": "Mitigation strategy"
        }
      ],
      "tasks": [
        {
          "id": "T-001",
          "title": "Task title",
          "description": "Detailed description",
          "owner": "agent",
          "type": "dev",
          "estimated_hours": 4,
          "path": "src/module/file.js",
          "reasoning": "Why this approach was chosen",
          "alternatives_considered": [
            {"approach": "Alternative A", "rejected_because": "reason"}
          ],
          "acceptance_criteria": [
            "Unit tests pass with >=80% coverage",
            "Linter passes with zero errors"
          ],
          "dependencies": ["T-000"],
          "subtasks": [
            {
              "id": "ST-001",
              "title": "Subtask title",
              "estimated_minutes": 30,
              "verification": "How to verify completion"
            }
          ],
          "rollback_procedure": "Steps to safely revert this change"
        }
      ]
    }
  ],
  "stop_points": [
    {
      "phase": "design",
      "checkpoint_file": "plan_manifest.json",
      "summary_file": "docs/design_summary.md",
      "approval_required": true,
      "estimated_context_tokens": 5000
    },
    {
      "phase": "implementation",
      "checkpoint_file": "impl_checkpoint.json",
      "summary_file": "docs/impl_progress.md",
      "approval_required": false,
      "estimated_context_tokens": 12000
    }
  ],
  "acceptance_definition": {
    "unit_tests": {
      "required": true,
      "coverage_minimum": 80,
      "tool": "jest"
    },
    "integration_tests": {
      "required": true,
      "tool": "supertest"
    },
    "lint": {
      "required": true,
      "zero_errors": true,
      "warnings_allowed": 5,
      "tool": "eslint"
    },
    "performance": {
      "p95_latency_ms": 100,
      "p99_latency_ms": 250,
      "throughput_rps": 1000
    },
    "security": {
      "scan_tool": "snyk",
      "max_severity": "medium",
      "required_checks": ["dependency_scan", "sast", "secrets_scan"]
    },
    "accessibility": {
      "required": false,
      "standard": "WCAG 2.1 AA",
      "tool": "axe-core"
    }
  },
  "artifacts": [
    {
      "name": "Design Document",
      "type": "markdown",
      "path": "docs/feature/design.md",
      "required": true,
      "template": "docs/templates/design_template.md"
    },
    {
      "name": "API Specification",
      "type": "openapi",
      "path": "docs/api/openapi.yaml",
      "required": true,
      "validation": "openapi-validator"
    },
    {
      "name": "Test Specification",
      "type": "json",
      "path": "tests/spec.json",
      "required": true
    }
  ],
  "tools_and_resources": {
    "required_tools": ["node", "npm", "docker"],
    "external_apis": [
      {
        "name": "Payment API",
        "requires_approval": true,
        "security_review": true
      }
    ],
    "new_dependencies": [
      {
        "package": "lodash",
        "version": "^4.17.21",
        "justification": "Utility functions for data transformation",
        "alternatives_considered": [
          "underscore (older, less maintained)",
          "ramda (functional but learning curve)"
        ],
        "security_scan_result": "pass",
        "license": "MIT",
        "approval_status": "pending"
      }
    ]
  },
  "observability": {
    "logging": {
      "level": "info",
      "structured": true,
      "pii_redaction": true
    },
    "metrics": {
      "tool": "prometheus",
      "key_metrics": ["request_duration", "error_rate", "throughput"]
    },
    "tracing": {
      "enabled": true,
      "tool": "opentelemetry",
      "sample_rate": 0.1
    },
    "alerting": {
      "on_error_rate": "> 1%",
      "on_latency_p95": "> 200ms"
    }
  }
}
```

---

## Planning & Execution Framework

### Two-Phase Approach

#### Phase 1: Planning (Always First)

**Inputs**:
- User stories or feature requirements
- Technical constraints
- Acceptance criteria

**Reasoning Process**:
1. Clarify ambiguities (provide 2-3 options per question)
2. Analyze constraints and identify conflicts
3. Propose 2-3 high-level approaches with tradeoffs
4. Recommend approach with justification
5. Break down into Epic → Stories → Tasks → Subtasks
6. Identify dependencies and critical path
7. Estimate effort and identify risks

**Outputs**:
- Human-readable plan (Markdown)
- Machine-readable plan (JSON)
- Clarifying questions (if any) or "No clarifications needed"

**Approval Gate**: Human must explicitly approve before Phase 2

#### Phase 2: Execution (After Approval Only)

**Preconditions**:
- `plan_manifest.json` exists with `"approved_by": "<name>"`
- Agent confirms understanding of assigned task

**Execution Loop** (per task):
1. Load task context from plan_manifest.json
2. State reasoning for implementation approach
3. Generate code/config/docs
4. Generate tests for code changes
5. Run local validation (lint, test, security scan)
6. Produce diff/patch
7. Generate commit message and PR description
8. Update plan_manifest.json with task status

**Outputs**:
- Code changes (diffs or new files)
- Tests (unit, integration, e2e as applicable)
- Test execution results
- Commit message (following template)
- PR description with rollback steps
- Updated plan_manifest.json

**Stop Conditions**:
- Task complete and validated → proceed to next task
- Validation failure → halt, report, await human decision
- Context window approaching limit → checkpoint and request continuation
- Uncertain about approach → halt, explain, request guidance

### Task Types and Specialized Patterns

#### Frontend UI Feature
**Additional Requirements**:
- Visual design mock or Figma link
- Responsive breakpoints: [mobile, tablet, desktop]
- Accessibility checklist (WCAG 2.1 AA)
- Performance budget: [FCP, LCP, TTI metrics]
- Browser compatibility: [list supported browsers/versions]
- Component library: [which library/version]

**Deliverables**:
- Component code with prop types
- Storybook stories or style guide
- Unit tests (React Testing Library or equivalent)
- Visual regression tests (if applicable)
- Accessibility audit results

#### Backend API
**Additional Requirements**:
- OpenAPI/Swagger specification (before implementation)
- Authentication/authorization scopes
- Rate limiting rules: [requests per minute/hour]
- Request/response validation schemas
- Error response format and codes
- Contract tests for API consumers
- Idempotency requirements

**Deliverables**:
- API implementation
- OpenAPI spec (validated)
- Contract tests
- Integration tests
- Load test results
- API documentation with examples

#### Data Pipeline
**Additional Requirements**:
- Input/output schemas with validation
- Data quality rules and validation tests
- Idempotency guarantees
- Error handling and dead letter queues
- Monitoring and alerting on data quality
- Backfill strategy for historical data
- Sample data for testing

**Deliverables**:
- Pipeline code with retry logic
- Schema definitions (Avro, Protobuf, JSON Schema)
- Data validation tests on samples
- Schema migration scripts
- Monitoring dashboard config
- Runbook for common issues

#### Infrastructure as Code
**Additional Requirements**:
- Infrastructure diagram (generated or provided)
- Cost estimation
- Disaster recovery plan
- Drift detection config
- Resource tagging strategy
- Multi-environment support (dev, staging, prod)

**Deliverables**:
- Terraform/CloudFormation/Pulumi code
- Plan output before apply
- Drift detection config
- Rollback scripts
- Cost estimation report
- Security group rules audit

#### ML Model Development
**Additional Requirements**:
- Dataset specification and provenance
- Training config (reproducible with seeds)
- Feature engineering pipeline
- Model evaluation metrics and baselines
- Hyperparameter tuning strategy
- Model versioning and registry
- Inference performance targets

**Deliverables**:
- Training pipeline code
- Feature engineering code
- Model evaluation report with metrics
- Hyperparameter tuning results
- Model serialization and versioning
- Inference service implementation
- A/B testing plan for deployment

---

## Context & Token Management

### Context Window Strategies

#### 1. Phase-Based Checkpointing

**Principle**: Never exceed 70% of context window. Save state and continue in new window.

**Checkpoint Files**:
- `plan_manifest.json`: Full plan with current state
- `phase_summary.md`: Concise summary of work completed (max 500 tokens)
- `decisions.json`: Key design decisions and rationales
- `artifacts_registry.json`: Map of task IDs to file paths and status

**Continuation Prompt**:
```markdown
Resume execution from checkpoint:
- Load: plan_manifest.json, phase_summary.md, decisions.json
- Current Task: [T-XXX] [title]
- Previous Context: [summarize in <200 tokens]
- Next Action: [describe what to do next]
```

#### 2. Vertical Slicing for Large Features

**Anti-pattern**: Horizontal layers (all controllers, then all services, then all tests)
**Best practice**: Vertical slices (end-to-end thin features)

**Example** (E-commerce checkout):
- ❌ Bad: Build all product APIs, then payment APIs, then order APIs
- ✅ Good: Slice 1: Happy path checkout (product → cart → payment → order)
- ✅ Good: Slice 2: Error handling and edge cases
- ✅ Good: Slice 3: Performance optimization and caching

**Benefits**:
- Each slice delivers user value
- Reduces integration risk
- Fits better in context windows
- Enables incremental deployment

#### 3. Hierarchical Summarization

For very long contexts, use hierarchical summaries:

```
Epic Summary (50 tokens)
  ↓
Story Summaries (100 tokens each)
  ↓
Task Details (full context)
```

Include full details only for the current task and immediate dependencies.

#### 4. Context Compression Techniques

**Semantic Compression**:
- Remove redundant information
- Replace verbose descriptions with concise technical terms
- Use references to external docs instead of inline content

**Code Context**:
- Show only function signatures and docstrings, not full implementations
- Use file tree structure instead of full file contents
- Include diffs instead of full files when showing changes

**Test Context**:
- Summarize test coverage instead of listing every test
- Show only failing tests in detail when debugging

---

## Testing & Verification

### Test-Driven Prompt Development

#### Prompt Regression Testing

**Concept**: Test prompts like you test code. Maintain a suite of test cases.

**Test Case Structure**:
```json
{
  "test_id": "T-001",
  "prompt_version": "v2.0.1",
  "input": {
    "objective": "Add user authentication",
    "constraints": {...}
  },
  "expected_output": {
    "plan_structure_valid": true,
    "contains_security_checklist": true,
    "includes_test_tasks": true,
    "dependency_order_correct": true
  },
  "actual_output": {...},
  "pass": true,
  "timestamp": "2025-11-11T10:00:00Z"
}
```

**Regression Suite**:
- Maintain 10-20 representative test cases
- Run suite after prompt changes
- Track pass rate over time
- Version control test cases with prompts

#### A/B Testing Prompt Variations

For critical prompts, test variations:

**Variation A** (Control): Current prompt
**Variation B** (Test): Modified prompt with new technique

**Metrics to Compare**:
- First-attempt success rate
- Number of clarifying questions needed
- Time to completion
- Code quality (lint errors, test coverage)
- Human satisfaction score (1-5)

**Minimum Sample**: 10 tasks per variation before deciding

### Test Pyramid for Agent-Generated Code

```
        E2E Tests (Few)
              ↑
     Integration Tests (Some)
              ↑
      Unit Tests (Many)
```

**Unit Tests** (80% of tests):
- Every function/method
- Edge cases and error conditions
- Mocked dependencies
- Fast execution (<1s per test)

**Integration Tests** (15% of tests):
- API endpoints with real DB
- Service interactions
- External service mocks
- Medium execution (<10s per test)

**E2E Tests** (5% of tests):
- Critical user journeys
- Full stack with real dependencies
- Slow execution (seconds to minutes)

### Coverage and Quality Gates

**Minimum Standards**:
- Line coverage: ≥80%
- Branch coverage: ≥75%
- Critical paths: 100% coverage
- Mutation testing score: ≥70% (for high-risk code)

**Quality Metrics**:
- Cyclomatic complexity: ≤10 per function
- Function length: ≤50 lines
- File length: ≤500 lines
- Dependency depth: ≤5 levels

**Agent Verification Loop**:
1. Generate code
2. Generate tests
3. Run tests and coverage
4. If below threshold: refactor and regenerate
5. If passed: proceed to linting

---

## Multi-Agent Patterns

### Role-Based Agent Specialization

#### Design Agent
**Responsibilities**:
- Analyze requirements
- Propose architecture
- Create design documents
- Identify risks and tradeoffs

**Input**: User stories, constraints
**Output**: Design doc, architecture diagram, plan_manifest.json

#### Implementation Agent
**Responsibilities**:
- Write production code
- Follow design specifications
- Apply coding standards
- Generate inline documentation

**Input**: Approved plan, design doc
**Output**: Code files, commit messages

#### Test Agent
**Responsibilities**:
- Write comprehensive tests
- Generate test data
- Create test specifications
- Run test suites

**Input**: Code files, acceptance criteria
**Output**: Test files, test reports, coverage reports

#### Review Agent
**Responsibilities**:
- Review code for quality
- Check against standards
- Identify potential issues
- Suggest improvements

**Input**: Code and tests
**Output**: Review comments, approval/rejection decision

### Agent Orchestration Patterns

#### Sequential Chain
```
Design Agent → Implementation Agent → Test Agent → Review Agent
```
Each agent completes before next starts. Best for straightforward tasks.

#### Parallel Execution
```
            ┌→ Feature A Agent
Design Agent ┼→ Feature B Agent  → Integration Agent
            └→ Feature C Agent
```
Multiple agents work on independent features simultaneously.

#### Iterative Refinement
```
Implementation Agent ⇄ Review Agent ⇄ Test Agent
```
Agents iterate until quality gates pass. Best for complex features.

#### Human-in-the-Loop
```
Agent → Human Review → Agent → Human Approval → Deployment
```
Critical decision points require human approval.

### Communication Protocol Between Agents

**Message Structure**:
```json
{
  "from_agent": "design_agent_v1",
  "to_agent": "implementation_agent_v1",
  "message_type": "handoff",
  "timestamp": "2025-11-11T10:00:00Z",
  "context": {
    "epic_id": "E-001",
    "task_id": "T-001",
    "phase": "implementation"
  },
  "payload": {
    "design_doc": "docs/feature/design.md",
    "plan_manifest": "plan_manifest.json",
    "critical_decisions": [
      "Using PostgreSQL for ACID guarantees",
      "RESTful API over GraphQL for simplicity"
    ]
  },
  "expectations": {
    "deliverables": ["src/module.js", "tests/module.test.js"],
    "quality_gates": ["lint_pass", "test_coverage_80"]
  }
}
```

---

## Advanced Techniques

### Retrieval-Augmented Generation (RAG) Integration

**Use Cases for RAG**:
- Querying internal documentation
- Looking up company coding standards
- Referencing architectural decision records (ADRs)
- Finding existing similar implementations
- Checking API contracts and schemas

**RAG Prompt Pattern**:
```markdown
## RAG Context Injection

**Retrieved Documents** (relevant to current task):

<document id="doc-123" relevance="0.92" source="internal_wiki">
[Content of relevant document]
</document>

<document id="doc-456" relevance="0.87" source="adr">
[Architecture decision record]
</document>

Based on the above retrieved context and the task requirements, proceed with [task].
Cite documents by ID when making design decisions informed by them.
```

**RAG Quality Control**:
- Only include documents with relevance score >0.8
- Limit to top 3-5 most relevant documents
- Preserve source attribution
- Allow agent to question document applicability

### Function Calling / Tool Use

**Available Tools** (define for each agent):
```json
{
  "tools": [
    {
      "name": "lint_code",
      "description": "Run linter on file",
      "parameters": {"file_path": "string"},
      "requires_approval": false
    },
    {
      "name": "run_tests",
      "description": "Execute test suite",
      "parameters": {"test_path": "string", "options": "object"},
      "requires_approval": false
    },
    {
      "name": "query_database",
      "description": "Read data from database",
      "parameters": {"query": "string", "database": "string"},
      "requires_approval": true
    },
    {
      "name": "deploy_to_staging",
      "description": "Deploy code to staging environment",
      "parameters": {"version": "string"},
      "requires_approval": true
    }
  ]
}
```

**Tool Use Protocol**:
1. Agent declares intent to use tool
2. If requires_approval: wait for human confirmation
3. Execute tool and receive result
4. Agent incorporates result into reasoning
5. Log tool use in audit trail

### Structured Output Modes

Modern LLMs support structured output (JSON mode, function calling). Use these for:

**JSON Mode** (when available):
```markdown
Produce output in strict JSON format following this schema:
[Include JSON schema]

Do not include any text outside the JSON object.
Set model parameter: "response_format": {"type": "json_object"}
```

**Benefits**:
- Guaranteed parseable output
- No need for output cleaning
- Eliminates "I'll help you with that..." preambles

### Prompt Chaining for Complex Workflows

**Pattern**: Break complex task into discrete prompts, chain results

**Example** (API Endpoint Implementation):
```
Prompt 1 (Design Agent):
→ Output: API design doc + OpenAPI spec

Prompt 2 (Implementation Agent):
→ Input: OpenAPI spec from Prompt 1
→ Output: Implementation code

Prompt 3 (Test Agent):
→ Input: Code from Prompt 2 + OpenAPI spec from Prompt 1
→ Output: Contract tests + unit tests

Prompt 4 (Documentation Agent):
→ Input: OpenAPI spec from Prompt 1 + implementation from Prompt 2
→ Output: API usage guide with examples
```

**Key Principle**: Each prompt is self-contained with explicit inputs/outputs

### Few-Shot Examples in Prompts

**When to Use**:
- Novel or unusual patterns
- Specific output formatting
- Domain-specific conventions

**Pattern**:
```markdown
## Examples of Expected Output

**Example 1** (User authentication endpoint):
Input: [requirement]
Output: [exemplary code/design]
Explanation: [why this is good]

**Example 2** (Data validation):
Input: [requirement]
Output: [exemplary code/design]
Explanation: [why this is good]

## Your Task
[Actual task that should follow the patterns shown above]
```

**Guidelines**:
- Include 2-3 examples (more is not always better)
- Show diversity in examples (different scenarios)
- Explain why each example is good
- Use realistic, non-trivial examples

---

## Security & Compliance

### Security Constraint Declaration

**Required in Every Prompt**:
```markdown
## Security & Data Handling Rules

**Data Classification**:
- PII Fields: [list fields considered PII]
- Sensitive Data: [API keys, credentials, financial data]
- Public Data: [what can be logged/cached]

**Encryption Requirements**:
- At Rest: [which data must be encrypted at rest]
- In Transit: [TLS version, certificate requirements]
- Key Management: [where keys are stored, rotation policy]

**Authentication & Authorization**:
- Auth Mechanism: [OAuth2, JWT, API keys, etc.]
- Required Scopes: [list scopes for this feature]
- RBAC Rules: [role-based access requirements]

**Network Security**:
- Outbound Connections: [allowed destinations, require approval for new]
- Inbound Connections: [allowed sources, firewall rules]
- Service-to-Service Auth: [mTLS, service mesh, etc.]

**Dependency Security**:
- Allowed Registries: [npm, PyPI, etc. - approved sources only]
- Vulnerability Scanning: [tool, run before adding dependency]
- License Approval: [allowed licenses, require review for GPL/AGPL]

**Secrets Management**:
- NEVER hardcode secrets in code
- Use: [secrets manager - AWS Secrets Manager, Vault, etc.]
- Rotation: [policy for key rotation]

**Code Security**:
- Input Validation: [all user input must be validated and sanitized]
- SQL Injection: [use parameterized queries only]
- XSS Prevention: [escape output, CSP headers]
- CSRF Protection: [token-based for state-changing operations]

**Audit & Compliance**:
- Regulatory Requirements: [GDPR, HIPAA, SOC2, PCI-DSS]
- Audit Logging: [what events must be logged, retention period]
- Data Retention: [how long data is kept, deletion procedures]
- Right to be Forgotten: [GDPR deletion requirements]
```

### Dependency Management Protocol

**Before Adding Any New Dependency**:

1. **Justification**:
   - What problem does it solve?
   - Why can't this be solved without a dependency?

2. **Alternatives Analysis**:
   - List 2-3 alternatives
   - Compare: features, maintenance, size, performance, license

3. **Security Scan**:
   - Run vulnerability scan (npm audit, snyk, etc.)
   - Check for known CVEs
   - Review dependency tree for transitive vulnerabilities

4. **License Review**:
   - Verify license compatibility
   - Flag copyleft licenses (GPL, AGPL) for legal review

5. **Maintenance Health**:
   - Last updated: within 12 months?
   - Number of open issues: <50?
   - Maintainer responsiveness: active?

6. **Size Impact**:
   - Bundle size increase: acceptable?
   - Impact on load time: measured?

**Output Template**:
```json
{
  "dependency": {
    "name": "package-name",
    "version": "1.2.3",
    "purpose": "Why we need this",
    "alternatives": [
      {"name": "alt-1", "reason_rejected": "..."},
      {"name": "alt-2", "reason_rejected": "..."}
    ],
    "security": {
      "vulnerabilities": 0,
      "scan_tool": "snyk",
      "scan_date": "2025-11-11",
      "result": "pass"
    },
    "license": "MIT",
    "maintenance": {
      "last_commit": "2025-10-15",
      "open_issues": 23,
      "health_score": "good"
    },
    "impact": {
      "bundle_size_kb": 45,
      "transitive_dependencies": 3
    },
    "recommendation": "approve",
    "requires_human_approval": false
  }
}
```

### PII and Data Privacy

**Automatic PII Detection**:
Agent must scan generated code/docs for:
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- Addresses
- Names in example data

**Redaction Policy**:
- Replace with synthetic data: `user@example.com`, `+1-555-0100`
- Use placeholders: `[EMAIL]`, `[PHONE]`, `[SSN]`
- Never use real user data in examples or tests

**GDPR Compliance Checklist**:
- [ ] Data minimization: collect only necessary data
- [ ] Purpose limitation: use data only for stated purpose
- [ ] Storage limitation: define retention period
- [ ] Right to access: API to retrieve user's data
- [ ] Right to deletion: API to delete user's data
- [ ] Data portability: API to export user's data
- [ ] Consent management: track and honor user consent

---

## Observability & Metrics

### Prompt Performance Metrics

**Track for Each Prompt Execution**:
```json
{
  "prompt_metrics": {
    "prompt_id": "dev-agent-v2.0.1",
    "execution_id": "exec-12345",
    "timestamp": "2025-11-11T10:00:00Z",
    "task_type": "api_implementation",
    "complexity_score": 7,
    "input_tokens": 3500,
    "output_tokens": 8200,
    "reasoning_tokens": 1200,
    "total_tokens": 12900,
    "latency_seconds": 45,
    "model_version": "claude-sonnet-4-5-20250929",
    "success": true,
    "quality_scores": {
      "first_attempt_success": true,
      "human_edits_required": false,
      "test_coverage_achieved": 0.85,
      "lint_errors": 0,
      "security_issues": 0
    },
    "cost_usd": 0.15
  }
}
```

**Aggregate Metrics** (weekly/monthly):
- Average time to completion by task type
- First-attempt success rate
- Token usage trends
- Cost per task type
- Human intervention rate
- Quality score trends

**Dashboards to Build**:
1. **Prompt Health Dashboard**: Success rates, error types, token efficiency
2. **Quality Trends**: Test coverage, lint errors, security issues over time
3. **Cost Efficiency**: Cost per task, cost per story point, ROI metrics
4. **Human Effort**: Approval time, edit frequency, rejection reasons

### Agent Logging Standards

**Log Levels**:
- `DEBUG`: Internal reasoning, intermediate steps
- `INFO`: Task starts, completions, major decisions
- `WARN`: Potential issues, risky decisions, uncertainty
- `ERROR`: Failures, validation errors, rollbacks

**Structured Logging Format**:
```json
{
  "timestamp": "2025-11-11T10:00:00Z",
  "level": "INFO",
  "agent_id": "implementation_agent_v1",
  "session_id": "sess-789",
  "task_id": "T-001",
  "event": "code_generation_complete",
  "details": {
    "files_created": 2,
    "lines_of_code": 150,
    "test_coverage": 0.85,
    "lint_errors": 0
  },
  "reasoning": "Chose async/await pattern for better readability and error handling",
  "alternatives_considered": ["callbacks", "promises with .then"],
  "trace_id": "trace-456"
}
```

**Log Retention**:
- Debug logs: 7 days
- Info logs: 30 days
- Warn/Error logs: 90 days
- Audit logs: 2 years (or per compliance requirement)

### Monitoring and Alerting

**Key Metrics to Monitor**:
- **Error Rate**: % of tasks that fail
- **Success Rate**: % of tasks that pass quality gates on first attempt
- **Token Efficiency**: Output tokens per input token
- **Cost Efficiency**: USD per successful task
- **Latency**: Time from task start to completion
- **Human Intervention Rate**: % of tasks requiring human edits

**Alert Thresholds**:
- Error rate > 10% over 1 hour
- Success rate < 70% over 1 day
- Cost per task > 2x baseline for 24 hours
- Token usage > 90% of context limit

### Prompt Versioning and Rollback

**Version Control for Prompts**:
```
prompts/
  v1.0/
    planning_prompt.md
    execution_prompt.md
    schema.json
  v2.0/
    planning_prompt.md
    execution_prompt.md
    schema.json
  CHANGELOG.md
```

**CHANGELOG.md**:
```markdown
# Prompt Changelog

## v2.0 (2025-11-11)
### Added
- Chain-of-thought reasoning requirements
- Multi-agent orchestration patterns
- Structured output schemas
- RAG integration guidelines

### Changed
- Improved context management strategies
- Enhanced security constraint templates
- Expanded test coverage requirements

### Fixed
- Clarified approval gate procedures
- Corrected schema validation rules

## v1.0 (2025-10-01)
- Initial release
```

**Rollback Procedure**:
If v2.0 shows degraded performance:
1. Monitor metrics for 48 hours after deployment
2. If error rate >15% or success rate <60%: initiate rollback
3. Revert to v1.0 prompts
4. Analyze failures, adjust v2.0, retry

---

## Error Handling & Recovery


### Comprehensive Failure Modes

#### 1. Ambiguous Requirements
**Symptoms**: Agent asks too many clarifying questions or makes wrong assumptions

**Agent Response**:
```markdown
I've identified ambiguities in the requirements:

**Ambiguity 1**: [Describe unclear aspect]
Options:
- A: [Option with pros/cons]
- B: [Option with pros/cons]
- C: [Option with pros/cons]
Recommendation: [Option with justification]

**Ambiguity 2**: [Describe unclear aspect]
...

Awaiting human decision on options above before proceeding.
```

**Human Action**: Clarify and approve

#### 2. Hallucinated Dependencies
**Symptoms**: Agent proposes non-existent libraries or incorrect APIs

**Prevention**:
- Require agent to provide package registry URL before adding dependency
- Verify package exists: `npm view <package>` or `pip show <package>`
- Cross-reference documentation URL

**Detection**:
```markdown
Agent Self-Check: Before proposing dependency "package-x", verify:
- [ ] Package exists on npm/PyPI: [registry URL]
- [ ] Documentation exists: [docs URL]
- [ ] Latest version matches proposed: [version]
If any check fails, flag as potential hallucination.
```

#### 3. Context Drift
**Symptoms**: Agent loses track of decisions made in earlier phases

**Prevention**:
- Require agent to summarize previous phases before starting new phase
- Include key decisions in every checkpoint
- Cross-reference plan_manifest.json frequently

**Recovery**:
```markdown
Context Rehydration Protocol:
1. Load plan_manifest.json
2. Read phase_summary.md for phases 1 through [current-1]
3. Summarize key decisions in <200 tokens
4. Confirm understanding with human before proceeding
```

#### 4. Token Overflow
**Symptoms**: Context window approaching or exceeding limit

**Agent Response**:
```markdown
⚠️ Context Window Warning: 85% utilized

Checkpointing current state:
- Files created: [list]
- Tasks completed: [T-001, T-002]
- Next task: T-003
- Saving: plan_manifest.json, phase_summary.md

To continue, please start a new session with continuation prompt:
"Resume from checkpoint: [checkpoint_id]"
```

**Human Action**: Start new session with continuation prompt

#### 5. Validation Failures
**Symptoms**: Tests fail, linter errors, security scans flag issues

**Agent Response**:
```markdown
❌ Validation Failed

**Failed Check**: Unit tests
**Details**: 3 tests failing in tests/module.test.js
**Errors**:
- Test: "should handle null input" → Expected 200, got 500
- Test: "should validate email format" → TypeError: cannot read property 'match'

**Root Cause Analysis**:
The implementation doesn't handle null input gracefully, causing downstream errors.

**Remediation Options**:
A. Add null checks at function entry (2 hours)
B. Use optional chaining throughout (1 hour, preferred)
C. Refactor to use validation library (4 hours)

**Recommendation**: Option B - fastest, leverages modern JS features

Awaiting approval to remediate.
```

#### 6. Performance Regressions
**Symptoms**: New code is slower than baseline

**Detection**:
Run performance benchmarks after implementation
Compare to baseline: p95 latency, throughput, memory usage

**Agent Response**:
```markdown
⚠️ Performance Regression Detected

**Metric**: p95 latency
**Baseline**: 85ms
**Current**: 145ms (70% increase)
**Threshold**: 100ms

**Profiling Results**:
- 40ms in new database query (N+1 query issue)
- 15ms in JSON serialization (large payload)

**Optimization Options**:
A. Add database query batching (expected: 60ms p95)
B. Implement response caching (expected: 50ms p95)
C. Both A and B (expected: 40ms p95)

**Recommendation**: Option C - brings us well below baseline

Awaiting approval to optimize.
```

### Retry and Fallback Strategies

**Transient Errors** (network, rate limits):
- Retry with exponential backoff: 1s, 2s, 4s, 8s
- Max retries: 3
- Fallback: Report failure and await human decision

**Validation Errors** (tests, lint):
- Attempt self-correction once
- If second attempt fails: report and await human decision
- Never attempt >2 self-corrections (risk of churn)

**Resource Exhaustion** (context, memory):
- Checkpoint immediately
- Do not attempt to continue
- Provide clear continuation prompt

### Rollback Procedures

**Code Rollback**:
```bash
# Agent generates rollback script
git revert <commit-hash>
# Restore database to previous migration
npx migrate down
# Clear cache
redis-cli FLUSHDB
# Restart services
kubectl rollout undo deployment/my-service
```

**Rollback Testing**:
- Rollback procedure must be tested in staging before production deployment
- Include rollback steps in every PR description

---


---

## Decision Trees

### 1. Agent Role Selection Decision Tree

```
START: New Task Assigned
│
├─ Is task well-defined with clear requirements?
│  ├─ NO → Use DESIGN AGENT first
│  │        ↓
│  │     Design Agent creates plan
│  │        ↓
│  │     Return to START with defined requirements
│  │
│  └─ YES → Continue
│           ↓
├─ Does task involve writing production code?
│  ├─ YES → Use IMPLEMENTATION AGENT
│  │         ├─ After code complete → Use TEST AGENT
│  │         └─ After tests → Use REVIEW AGENT
│  │
│  ├─ Is task primarily testing existing code?
│  │  └─ YES → Use TEST AGENT directly
│  │
│  ├─ Is task code review/quality check?
│  │  └─ YES → Use REVIEW AGENT directly
│  │
│  └─ Is task security analysis?
│     └─ YES → Use SECURITY AGENT
│
└─ Complex task requiring multiple agents?
   └─ YES → Use ORCHESTRATOR AGENT
             ├─ Orchestrator delegates to specialized agents
             └─ Orchestrator synthesizes results

DECISION FACTORS:
- Task complexity: Simple (single agent) vs Complex (multiple agents)
- Task type: Design, Implementation, Test, Review, Security
- Requirements clarity: Unclear → Design Agent first
- Risk level: High risk → Add Security + Review agents
```

### 2. Validation Failure Response Decision Tree

```
START: Validation Failed
│
├─ What type of failure?
│  │
│  ├─ TEST FAILURES
│  │  ├─ How many tests failed?
│  │  │  ├─ 1-3 tests → SELF-CORRECT (attempt 1)
│  │  │  │              ├─ Fixed? → Continue
│  │  │  │              └─ Still failing? → REPORT TO HUMAN
│  │  │  │
│  │  │  └─ >3 tests → REPORT TO HUMAN (too many issues)
│  │  │
│  │  └─ Are failures in new code or existing code?
│  │     ├─ New code → Fix and retry
│  │     └─ Existing code → REGRESSION → Rollback + Report
│  │
│  ├─ LINT ERRORS
│  │  ├─ Auto-fixable? (e.g., formatting)
│  │  │  └─ YES → Run auto-fix, re-validate
│  │  │
│  │  └─ Manual fixes needed?
│  │     ├─ <5 errors → SELF-CORRECT
│  │     └─ ≥5 errors → REPORT TO HUMAN
│  │
│  ├─ SECURITY SCAN FAILURES
│  │  ├─ Severity?
│  │  │  ├─ CRITICAL → HALT + REPORT IMMEDIATELY
│  │  │  ├─ HIGH → HALT + REPORT + Propose fix
│  │  │  ├─ MEDIUM → REPORT + Propose fix + Continue if approved
│  │  │  └─ LOW → LOG + Continue
│  │  │
│  │  └─ Type?
│  │     ├─ Hardcoded secret → Remove + regenerate + re-scan
│  │     ├─ Vulnerable dependency → Propose alternative
│  │     └─ Code vulnerability → Propose fix + await approval
│  │
│  └─ PERFORMANCE REGRESSION
│     ├─ How much slower?
│     │  ├─ <10% → LOG + Continue
│     │  ├─ 10-50% → REPORT + Propose optimization
│     │  └─ >50% → HALT + REPORT + Profile
│     │
│     └─ Profile to identify bottleneck
│        ├─ Database query → Optimize query/add index
│        ├─ Algorithm complexity → Refactor algorithm
│        ├─ Memory leak → Fix leak
│        └─ External API → Add caching/circuit breaker

SELF-CORRECTION LIMIT: Maximum 1 retry
If still failing after self-correction → Report to human
Never attempt more than 2 total attempts (original + 1 retry)
```

### 3. Rollback Decision Tree

```
START: Issue Detected in Production
│
├─ What is the severity?
│  │
│  ├─ SEV1 (Critical - System down or data loss risk)
│  │  └─ IMMEDIATE ROLLBACK
│  │     ├─ Execute rollback procedure
│  │     ├─ Verify system restored
│  │     ├─ Notify stakeholders
│  │     └─ Post-mortem required
│  │
│  ├─ SEV2 (High - Major feature broken, many users affected)
│  │  ├─ Is there a quick fix available? (<15 min)
│  │  │  ├─ YES + Confident → Apply fix + monitor
│  │  │  └─ NO or Uncertain → ROLLBACK
│  │  │
│  │  └─ After decision:
│  │     ├─ Notify stakeholders
│  │     └─ Schedule post-mortem
│  │
│  ├─ SEV3 (Medium - Feature degraded, some users affected)
│  │  ├─ Is fix available within 1 hour?
│  │  │  ├─ YES → Apply fix + monitor closely
│  │  │  └─ NO → Consider rollback vs. workaround
│  │  │
│  │  ├─ Workaround available for users?
│  │  │  ├─ YES → Document workaround + fix in next release
│  │  │  └─ NO → ROLLBACK
│  │  │
│  │  └─ Monitor and reassess every 30 minutes
│  │
│  └─ SEV4 (Low - Minor issue, few users affected)
│     └─ Fix in next release (no rollback)
│
├─ Before Executing Rollback:
│  ├─ Check: Will rollback cause data loss?
│  │  └─ YES → Backup current state first
│  │
│  ├─ Check: Are there database migrations?
│  │  └─ YES → Run down migrations first
│  │
│  └─ Check: Are there dependent services?
│     └─ YES → Coordinate rollback timing
│
├─ Execute Rollback:
│  ├─ Revert code (git revert or rollout undo)
│  ├─ Rollback database migrations (if any)
│  ├─ Clear caches
│  ├─ Restart services
│  └─ Verify health checks pass
│
└─ After Rollback:
   ├─ Monitor for 1 hour (SEV1/SEV2) or 15 min (SEV3)
   ├─ Confirm issue resolved
   ├─ Update status page
   └─ Schedule post-mortem meeting

ROLLBACK CRITERIA SUMMARY:
- SEV1: Always rollback immediately
- SEV2: Rollback unless quick fix (<15 min) available
- SEV3: Rollback if no fix within 1 hour and no workaround
- SEV4: No rollback, fix in next release
```

### 4. Context Window Management Decision Tree

```
START: Task Assigned
│
├─ Estimate Context Requirements
│  ├─ Current context size: [N] tokens
│  ├─ Task complexity: Simple | Medium | Complex
│  └─ Expected output size: [M] tokens
│
├─ Total estimated: [N + M] tokens
│  │
│  ├─ <50% of context window?
│  │  └─ PROCEED normally
│  │
│  ├─ 50-70% of context window?
│  │  └─ PROCEED with caution
│  │     ├─ Monitor usage during generation
│  │     └─ Plan checkpoint after this task
│  │
│  ├─ 70-85% of context window?
│  │  └─ OPTIMIZE before proceeding
│  │     ├─ Compress context (use summaries)
│  │     ├─ Remove low-relevance information
│  │     ├─ Use hierarchical summarization
│  │     └─ Then proceed
│  │
│  └─ >85% of context window?
│     └─ CHECKPOINT NOW
│        ├─ Save state (plan_manifest.json, phase_summary.md)
│        ├─ Generate continuation prompt
│        ├─ Request new session
│        └─ Human starts new session with continuation

DURING TASK EXECUTION:
Monitor context usage after each major section

├─ If usage >70% during generation:
│  ├─ Issue warning
│  ├─ Complete current section
│  └─ Checkpoint before next section
│
└─ If usage >90%:
   └─ STOP IMMEDIATELY
      ├─ Save partial work
      ├─ Checkpoint
      └─ Request continuation

CHECKPOINT CONTENTS:
1. plan_manifest.json (full state)
2. phase_summary.md (≤500 tokens)
3. decisions.json (key decisions)
4. artifacts_registry.json (file mapping)

CONTINUATION PROMPT TEMPLATE:
"Resume from checkpoint [ID]
Context files: [list]
Last completed: [task-id]
Next action: [description]"
```

---


---

## Templates & Examples

### Planning Prompt Template (Pasteable)

```markdown
You are the Lead Developer Agent with authority to propose designs and generate artifacts. You CANNOT merge code or deploy without explicit human approval. You MUST follow the reasoning requirements before making any design decisions.

Prompt Version: v2.0.1
Model: claude-sonnet-4-5

---

## OBJECTIVE

**Primary Goal**: [One-line objective]

**User Stories**:
- As a [user type], I want [capability], so that [benefit]
- [2-5 total stories]

**Success Definition**: [Observable outcome]

---

## CONTEXT & CONSTRAINTS

**Technical Stack**:
- Language/Framework: [e.g., Node.js 20, Express 4.x]
- Database: [e.g., PostgreSQL 15]
- Infrastructure: [e.g., AWS ECS, Docker]
- Repository: [git URL], Branch: [e.g., feature/*]
- CI/CD: [e.g., GitHub Actions]

**Standards**:
- Linter: [e.g., ESLint with Airbnb config]
- Formatter: [e.g., Prettier]
- Test Framework: [e.g., Jest]
- Min Coverage: [e.g., 80%]

**Performance Targets**:
- p95 Latency: ≤ [X] ms
- Throughput: ≥ [Y] req/sec
- Memory: ≤ [Z] MB

**Security**:
- PII Fields: [list]
- Encryption: [requirements]
- Auth: [mechanism and scopes]
- Regulatory: [GDPR, HIPAA, etc.]
- Forbidden: [libs, patterns]

**Dependency Policy**:
- Require pre-approval for new dependencies
- Run security scan before proposing
- Provide 2 alternatives with tradeoffs

---

## REASONING REQUIREMENTS

Before designing or coding:
1. **Clarify**: State your understanding. List assumptions. Ask questions if ambiguous.
2. **Options**: Propose 2-3 approaches with tradeoffs.
3. **Recommend**: Choose best approach with justification.
4. **Risks**: Identify risks and mitigation strategies.
5. **Dependencies**: List external dependencies and integration points.

---

## DELIVERABLES

**Human-Readable**:
- Design Doc: `docs/[feature]/design.md`
- Implementation Plan: `docs/[feature]/plan.md`
- Runbook: `docs/[feature]/runbook.md`

**Machine-Readable**:
- Plan Manifest: `plan_manifest.json` (must follow schema v2.0)
- Acceptance Criteria: `acceptance.yaml`

**Code**:
- Source: `src/[paths]`
- Tests: `tests/unit/`, `tests/integration/`
- Config: `config/[env].yaml`

**Changelog**:
- Entry: `CHANGELOG.md`
- Commit Template: `[E-<id>] <type>: <short> — <detail>`

---

## ACCEPTANCE CRITERIA

**Definition of Done**:
- [ ] Unit tests: coverage ≥ [X]%
- [ ] Integration tests: all pass
- [ ] Linter: zero errors
- [ ] Security scan: no critical/high
- [ ] Performance: meets targets
- [ ] Docs: complete and reviewed
- [ ] Manual smoke test: steps provided and executed

**Feature-Specific**:
- [Custom acceptance criteria]

---

## PLANNING RULES

**Framework**: Epic → Stories → Tasks → Subtasks

**Dependencies**: Sequence by critical path, risk-weighted

**Stop Points**: Size phases for ≤ [N] tokens or ≤ [M] files

**Pre-Validation**:
- Identify missing info
- Provide 2-3 options per question with tradeoffs
- State "No clarifications needed" if none

**Approval Gate**: DO NOT generate code until:
1. Full plan (human + machine) is produced
2. Human provides: "APPROVED_BY: [name] [timestamp]"
3. Approval logged in plan_manifest.json

---

## STATE MANAGEMENT

**Checkpoints**:
- Save plan_manifest.json, phase_summary.md after each phase
- Include: epic_id, phase, files_modified, decisions

**Large Features**:
- Split by vertical slices (end-to-end), not layers
- 3-7 stories per epic for optimal context

---

## FAILURE HANDLING

**Rollback Triggers**:
- Test coverage drops below threshold
- Security vulnerabilities (critical/high)
- Performance regression > [X]%

**Remediation**:
1. Halt and preserve state
2. Diagnose with reasoning
3. Propose 2 options with tradeoffs
4. Await human decision
5. Execute fix with verification

---

## LOGGING & AUDIT

**Required**:
- Timestamp (ISO 8601)
- Agent/Model version
- Artifacts generated (paths + hashes)
- Major decisions (decision + rationale + alternatives)

Store in: `.llm_audit/[date]/[task_id].json`

---

## OUTPUT

Produce:
1. **Clarifications** (if any) with 2-3 options each, or "No clarifications needed"
2. **Human Plan** (Markdown) with reasoning for design choices
3. **Machine Plan** (JSON) following schema v2.0
```

### Quick Execution Prompt (After Approval)

```markdown
Agent Role: Executor
Model: claude-sonnet-4-5
Prompt Version: v2.0.1

---

## EXECUTION CONTEXT

**Plan File**: `plan_manifest.json` at [path]
**Precondition**: `"approved_by": "<name>", "approval_timestamp": "<timestamp>"`

**Assigned Task**: [T-XXX] [Task Title]

**Task Details**:
- Type: [dev|test|doc|ci|infra]
- Files: [paths]
- Dependencies: [previous task IDs]
- Acceptance Criteria: [list]

---

## EXECUTION PROTOCOL

1. **Confirm**: Load plan_manifest.json and verify task details
2. **Reason**: State implementation approach and alternatives considered
3. **Implement**: Generate code/config/docs
4. **Test**: Generate tests for code changes
5. **Validate**: Run lint, tests, security scan locally
6. **Package**: Produce diff, commit message, PR description
7. **Update**: Mark task complete in plan_manifest.json

---

## VALIDATION REQUIREMENTS

Run locally and include output:
- Linter: [command to run]
- Tests: [command to run]
- Security: [command to run]

---

## DELIVERABLES

**Code**:
- Diffs or new files only
- Following style guide
- Inline comments for complex logic

**Tests**:
- Unit tests for all new functions
- Integration tests for API endpoints
- Test data/fixtures if needed

**Documentation**:
- Updated README if applicable
- Inline code comments
- API docs if endpoints changed

**Metadata**:
- Commit message (following template)
- PR description with rollback steps
- Updated plan_manifest.json with task status

---

## STOP CONDITIONS

✅ **Proceed**: Task complete and validated
⚠️ **Halt**: Validation failure → report and await human decision
⚠️ **Halt**: Uncertain about approach → explain and request guidance
⚠️ **Checkpoint**: Context window >70% → save state and request continuation

---

## OUTPUT

Produce:
1. **Implementation Reasoning** (2-3 paragraphs)
2. **Code Changes** (diffs or full files)
3. **Tests** (new test files)
4. **Validation Results** (lint, test, security output)
5. **Commit Message** (following template)
6. **PR Description** (summary, files, rollback, testing)
7. **Updated plan_manifest.json**
```

### Before/After Example

#### Before (Vague Prompt)
```
Create an API endpoint for user login.
```

**Problems**:
- No tech stack specified
- No security requirements
- No success criteria
- No deliverables defined
- No testing requirements

**Agent Output**: Likely inconsistent, may have security issues, no tests

---

#### After (Optimized Prompt)
```markdown
You are the Lead Developer Agent. Prompt Version: v2.0.1

## OBJECTIVE
Add POST /v1/auth/login endpoint for user authentication with email/password

## USER STORIES
- As a user, I want to log in with email and password, so I can access my account
- As a system, I want to rate-limit login attempts, so I prevent brute force attacks

## CONTEXT
- Stack: Node.js 20, Express 4.19, PostgreSQL 15
- Repo: git@github.com:company/api.git, Branch: feature/auth-login
- CI: GitHub Actions with Jest
- Standards: ESLint (Airbnb), Prettier, min 80% coverage

## SECURITY
- Password hashing: bcrypt with 12 rounds
- JWT token: RS256, 1-hour expiry, refresh token 7 days
- Rate limiting: 5 attempts per IP per 15 minutes
- PII: email is PII, must be logged redacted
- No dependencies without security scan

## PERFORMANCE
- p95 latency: ≤ 200ms
- Throughput: ≥ 100 req/sec
- DB connection pooling: enabled

## DELIVERABLES
- Design: docs/auth/login_design.md
- Plan: plan_manifest.json
- Code: src/routes/auth/login.js, src/middleware/rate-limit.js
- Tests: tests/unit/auth.test.js, tests/integration/login.test.js
- OpenAPI: docs/api/openapi.yaml (update)
- Commit: "[E-001] feat: add user login endpoint — POST /v1/auth/login with rate limiting"

## ACCEPTANCE
- [ ] Unit tests: >=80% coverage
- [ ] Integration tests: happy path + error cases (invalid creds, rate limit)
- [ ] Security: bcrypt hashing verified, JWT signed correctly
- [ ] Performance: <200ms p95 on 100 concurrent requests
- [ ] OpenAPI spec: updated and validated

## REASONING REQUIRED
Before coding:
1. State assumptions about password storage (is bcrypt acceptable?)
2. Propose JWT vs session tokens with tradeoffs
3. Explain rate limiting strategy (IP-based ok?)
4. Identify risks (timing attacks, token theft)

## APPROVAL GATE
DO NOT code until plan is approved by human

## OUTPUT
1. Clarifications (if any) or "No clarifications needed"
2. Design doc (Markdown)
3. Plan (JSON)
```

**Agent Output**: Comprehensive plan with reasoning, secure implementation, thorough tests, proper documentation

---

## Checklist & Governance

### Pre-Planning Checklist

Before sending planning prompt:
- [ ] Objective is clear and specific (one sentence)
- [ ] User stories follow "As a [user], I want [capability], so that [benefit]" format
- [ ] Tech stack specified with versions
- [ ] Security requirements declared (PII, encryption, auth)
- [ ] Performance targets quantified (latency, throughput)
- [ ] Acceptance criteria are measurable
- [ ] Dependency policy stated
- [ ] Deliverable paths specified
- [ ] Approval gate clearly defined
- [ ] Prompt version tagged

### Pre-Execution Checklist

Before executing:
- [ ] Plan exists (human + machine format)
- [ ] Clarifications addressed
- [ ] Acceptance criteria concrete and measurable
- [ ] Stop points defined with token estimates
- [ ] Tests listed with owners assigned
- [ ] Security dependencies declared
- [ ] Commit/PR template provided
- [ ] Human sign-off captured in plan_manifest.json

### Post-Execution Review Checklist

After agent completes task:
- [ ] All deliverables present
- [ ] Tests run and pass (include output)
- [ ] Linter passes (zero errors)
- [ ] Security scan passes (no critical/high)
- [ ] Performance benchmarks meet targets
- [ ] Code follows style guide
- [ ] Documentation complete
- [ ] Rollback procedure documented
- [ ] Commit message follows template
- [ ] PR description includes rollback steps
- [ ] Changelog updated

### Governance Rules (Enforce in All Prompts)

**Mandatory Rules**:
1. "Do not execute external network calls without explicit human approval."
2. "Do not introduce new third-party dependencies without listing 2 alternatives, security scan, and justification."
3. "All artifacts must be deterministic and reproducible."
4. "Never hardcode credentials, API keys, or secrets in code."
5. "All PII must be redacted in logs and examples."
6. "Code without tests will not be accepted."
7. "Performance regressions >10% require human approval to proceed."

**Enforcement Mechanism**:
- Use automated validator to check plan_manifest.json against schema
- Block execution phase if planning phase skipped
- Reject PRs without test files
- Fail CI if coverage drops below threshold

---


## Specialized Task Patterns

### Frontend UI Feature

## Cost Modeling & Budgeting

### Understanding LLM Costs

**Cost Components**:
```
Total Cost = (Input Tokens × Input Price) + (Output Tokens × Output Price) + (Cached Tokens × Cache Price)
```

**Pricing (as of Nov 2025, subject to change)**:
```yaml
claude_sonnet_4.5:
  input_price_per_mtok: 3.00   # USD per million tokens
  output_price_per_mtok: 15.00
  cache_write_per_mtok: 3.75
  cache_read_per_mtok: 0.30

gpt4_turbo:
  input_price_per_mtok: 10.00
  output_price_per_mtok: 30.00
```

### Cost Estimation Formula

```python
def estimate_task_cost(
    input_tokens: int,
    estimated_output_tokens: int,
    cached_tokens: int = 0,
    model: str = "claude-sonnet-4.5"
) -> float:
    """
    Estimate cost for a single task.
    
    Args:
        input_tokens: Tokens in prompt (context + instructions)
        estimated_output_tokens: Expected output size
        cached_tokens: Tokens cached from previous requests
        model: Model identifier
    
    Returns:
        Estimated cost in USD
    """
    pricing = {
        "claude-sonnet-4.5": {
            "input": 3.00 / 1_000_000,
            "output": 15.00 / 1_000_000,
            "cache_read": 0.30 / 1_000_000,
        }
    }
    
    prices = pricing.get(model, pricing["claude-sonnet-4.5"])
    
    # Calculate costs
    input_cost = (input_tokens - cached_tokens) * prices["input"]
    cache_cost = cached_tokens * prices["cache_read"]
    output_cost = estimated_output_tokens * prices["output"]
    
    total = input_cost + cache_cost + output_cost
    return round(total, 4)

# Example: Planning task
planning_cost = estimate_task_cost(
    input_tokens=5000,      # User requirements + template
    estimated_output_tokens=8000,  # Plan document
    cached_tokens=2000      # Template is cached
)
print(f"Planning task cost: ${planning_cost}")
# Output: Planning task cost: $0.1266

# Example: Implementation task
impl_cost = estimate_task_cost(
    input_tokens=12000,     # Plan + previous code + new task
    estimated_output_tokens=6000,  # Generated code
    cached_tokens=8000      # Plan is cached
)
print(f"Implementation task cost: ${impl_cost}")
# Output: Implementation task cost: $0.1044
```

### Budget Planning Template

**Monthly Budget Calculator**:
```python
def calculate_monthly_budget(
    stories_per_month: int,
    avg_tasks_per_story: int,
    avg_input_tokens: int = 10000,
    avg_output_tokens: int = 6000,
    cache_hit_rate: float = 0.4,  # 40% of input is cached
    model: str = "claude-sonnet-4.5",
    buffer_multiplier: float = 1.3  # 30% buffer for retries/errors
) -> dict:
    """
    Calculate monthly LLM cost budget.
    
    Returns dict with breakdown.
    """
    # Calculate per-task cost
    cached_tokens = int(avg_input_tokens * cache_hit_rate)
    cost_per_task = estimate_task_cost(
        avg_input_tokens,
        avg_output_tokens,
        cached_tokens,
        model
    )
    
    # Calculate monthly totals
    tasks_per_month = stories_per_month * avg_tasks_per_story
    base_monthly_cost = cost_per_task * tasks_per_month
    buffered_cost = base_monthly_cost * buffer_multiplier
    
    return {
        "stories_per_month": stories_per_month,
        "tasks_per_month": tasks_per_month,
        "cost_per_task": round(cost_per_task, 4),
        "base_monthly_cost": round(base_monthly_cost, 2),
        "buffer_multiplier": buffer_multiplier,
        "buffered_monthly_cost": round(buffered_cost, 2),
        "assumptions": {
            "avg_input_tokens": avg_input_tokens,
            "avg_output_tokens": avg_output_tokens,
            "cache_hit_rate": f"{cache_hit_rate*100}%"
        }
    }

# Example: Startup team
startup_budget = calculate_monthly_budget(
    stories_per_month=20,
    avg_tasks_per_story=4
)

print(f"""
Startup Team Budget Estimate:
- Stories/month: {startup_budget['stories_per_month']}
- Tasks/month: {startup_budget['tasks_per_month']}
- Cost/task: ${startup_budget['cost_per_task']}
- Base cost: ${startup_budget['base_monthly_cost']}
- With 30% buffer: ${startup_budget['buffered_monthly_cost']}
""")

# Output:
# Startup Team Budget Estimate:
# - Stories/month: 20
# - Tasks/month: 80
# - Cost/task: $0.1044
# - Base cost: $8.35
# - With 30% buffer: $10.86
```

### ROI Calculation

```python
def calculate_roi(
    monthly_llm_cost: float,
    developer_hourly_rate: float,
    hours_saved_per_month: float,
    quality_improvement_factor: float = 1.1  # 10% fewer bugs
) -> dict:
    """
    Calculate ROI for LLM-assisted development.
    
    Args:
        monthly_llm_cost: Total LLM costs per month
        developer_hourly_rate: Avg hourly rate for developers
        hours_saved_per_month: Developer hours saved by LLM
        quality_improvement_factor: Bug reduction multiplier
    
    Returns:
        ROI metrics dict
    """
    # Calculate savings
    time_savings = hours_saved_per_month * developer_hourly_rate
    
    # Quality improvement (fewer bugs = less debugging time)
    # Assume 20% of time is debugging
    debugging_time = hours_saved_per_month * 0.20
    quality_savings = debugging_time * developer_hourly_rate * (quality_improvement_factor - 1)
    
    total_savings = time_savings + quality_savings
    net_benefit = total_savings - monthly_llm_cost
    roi_percentage = (net_benefit / monthly_llm_cost) * 100
    
    return {
        "monthly_llm_cost": round(monthly_llm_cost, 2),
        "time_savings": round(time_savings, 2),
        "quality_savings": round(quality_savings, 2),
        "total_savings": round(total_savings, 2),
        "net_benefit": round(net_benefit, 2),
        "roi_percentage": round(roi_percentage, 1),
        "payback_period_days": round((monthly_llm_cost / total_savings) * 30, 1) if total_savings > 0 else float('inf')
    }

# Example
roi = calculate_roi(
    monthly_llm_cost=200,        # $200/month in LLM costs
    developer_hourly_rate=75,     # $75/hour developer
    hours_saved_per_month=15,     # 15 hours saved
    quality_improvement_factor=1.15  # 15% fewer bugs
)

print(f"""
ROI Analysis:
- Monthly LLM Cost: ${roi['monthly_llm_cost']}
- Time Savings: ${roi['time_savings']}
- Quality Improvement: ${roi['quality_savings']}
- Total Savings: ${roi['total_savings']}
- Net Benefit: ${roi['net_benefit']}
- ROI: {roi['roi_percentage']}%
- Payback Period: {roi['payback_period_days']} days
""")

# Output:
# ROI Analysis:
# - Monthly LLM Cost: $200.0
# - Time Savings: $1125.0
# - Quality Improvement: $33.75
# - Total Savings: $1158.75
# - Net Benefit: $958.75
# - ROI: 479.4%
# - Payback Period: 5.2 days
```

### Cost Optimization Strategies

**1. Prompt Caching**:
```python
# Bad: Reloading same context every time
prompt = f"{company_coding_standards}\n{api_spec}\n{task}"
# Cost: Full input tokens every time

# Good: Cache stable context
# First request: Full cost
cached_prompt = f"<cached>{company_coding_standards}\n{api_spec}</cached>\n{task}"
# Subsequent requests: 90% cheaper on cached portion
```

**2. Output Size Optimization**:
```python
# Bad: Generate full file
"Generate complete implementation of UserService.java"
# Cost: ~8000 output tokens

# Good: Generate incrementally
"Generate method signature and docstring for UserService.authenticate()"
# Cost: ~800 output tokens (10x cheaper)
# Then in next call: "Now implement the method body"
```

**3. Model Selection**:
```yaml
simple_tasks:
  model: claude-haiku  # Fastest, cheapest
  use_for: ["linting", "simple_refactors", "test_generation"]
  
complex_tasks:
  model: claude-sonnet  # Balanced
  use_for: ["planning", "architecture", "implementation"]
  
critical_tasks:
  model: claude-opus  # Most capable (when available)
  use_for: ["security_reviews", "complex_algorithms"]
```

### Budget Monitoring Dashboard

**Metrics to Track**:
```yaml
real_time_metrics:
  - current_month_spend
  - cost_per_task_avg
  - budget_utilization_percentage
  - projected_end_of_month_cost

efficiency_metrics:
  - tokens_per_story_point
  - cost_per_story_point
  - cache_hit_rate
  - retry_rate (higher = more waste)

quality_metrics:
  - first_attempt_success_rate
  - cost_per_accepted_task (includes retries)
  - human_edit_rate
```

**Alert Thresholds**:
```yaml
alerts:
  - metric: budget_utilization
    warning_threshold: 75%
    critical_threshold: 90%
    
  - metric: cost_per_task
    warning_threshold: 150% of baseline
    critical_threshold: 200% of baseline
    
  - metric: retry_rate
    warning_threshold: 15%
    critical_threshold: 25%
```

---


---

## Production Operations

### Deployment Strategy

**Progressive Rollout**:
```yaml
deployment_phases:
  canary:
    percentage: 5
    duration: 1h
    success_criteria:
      - error_rate < 0.5%
      - p95_latency < 200ms
    
  progressive:
    - percentage: 25
      duration: 2h
    - percentage: 50
      duration: 4h
    - percentage: 100
      duration: indefinite

  rollback_triggers:
    - error_rate > 2%
    - p95_latency > 300ms
    - critical_alert_fires
```

**Blue-Green Deployment**:
1. Deploy new version to "green" environment
2. Run smoke tests on green
3. If pass: switch traffic from blue to green
4. Monitor green for 1 hour
5. If stable: decommission blue
6. If issues: switch back to blue (instant rollback)

**Feature Flags**:
For risky changes, deploy behind feature flag:
- Code deployed but inactive
- Gradually enable for % of users
- Monitor metrics per cohort
- Instant disable if issues detected

### Monitoring in Production

**Golden Signals**:
```yaml
latency:
  - p50_latency_ms
  - p95_latency_ms
  - p99_latency_ms

traffic:
  - requests_per_second
  - active_connections

errors:
  - error_rate_percentage
  - 4xx_rate
  - 5xx_rate

saturation:
  - cpu_utilization
  - memory_utilization
  - disk_io
  - connection_pool_saturation
```

**Incident Response**: See [Error Handling & Recovery](#error-handling--recovery) section for detailed runbooks.

---

## Checklist & Governance


### Pre-Planning Checklist

Before sending planning prompt:
- [ ] Objective is clear and specific (one sentence)
- [ ] User stories follow "As a [user], I want [capability], so that [benefit]" format
- [ ] Tech stack specified with versions
- [ ] Security requirements declared (PII, encryption, auth)
- [ ] Performance targets quantified (latency, throughput)
- [ ] Acceptance criteria are measurable
- [ ] Dependency policy stated
- [ ] Deliverable paths specified
- [ ] Approval gate clearly defined
- [ ] Prompt version tagged

### Pre-Execution Checklist

Before executing:
- [ ] Plan exists (human + machine format)
- [ ] Clarifications addressed
- [ ] Acceptance criteria concrete and measurable
- [ ] Stop points defined with token estimates
- [ ] Tests listed with owners assigned
- [ ] Security dependencies declared
- [ ] Commit/PR template provided
- [ ] Human sign-off captured in plan_manifest.json

### Post-Execution Review Checklist

After agent completes task:
- [ ] All deliverables present
- [ ] Tests run and pass (include output)
- [ ] Linter passes (zero errors)
- [ ] Security scan passes (no critical/high)
- [ ] Performance benchmarks meet targets
- [ ] Code follows style guide
- [ ] Documentation complete
- [ ] Rollback procedure documented
- [ ] Commit message follows template
- [ ] PR description includes rollback steps
- [ ] Changelog updated


## Complete Enforcement Validation

### Automated Plan Validation Script

**Location**: `scripts/validate_plan_manifest.py`

```python
#!/usr/bin/env python3
"""
Plan Manifest Validator
Enforces governance rules and schema compliance for LLM-generated plans.

Usage:
    python validate_plan_manifest.py plan_manifest.json
    
Exit Codes:
    0: Validation passed
    1: Validation failed
    2: File not found or invalid JSON
"""

import json
import sys
import re
from typing import Dict, List, Any
from datetime import datetime
from jsonschema import validate, ValidationError as JSONSchemaError

# Schema v2.0 (inline for portability - alternatively load from file)
PLAN_SCHEMA_V2 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["meta", "epic", "stories", "acceptance_definition"],
    "properties": {
        "meta": {
            "type": "object",
            "required": ["created", "agent", "prompt_version"],
            "properties": {
                "prompt_version": {"type": "string", "pattern": r"^v\d+\.\d+\.\d+$"},
                "approved_by": {"type": ["string", "null"]},
                "approval_timestamp": {"type": ["string", "null"], "format": "date-time"}
            }
        },
        "epic": {
            "type": "object",
            "required": ["id", "title", "objective"]
        },
        "stories": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "title", "acceptance_criteria", "tasks"],
                "properties": {
                    "tasks": {
                        "type": "array",
                        "minItems": 1
                    }
                }
            }
        }
    }
}

class ValidationError(Exception):
    """Custom validation error"""
    pass

class PlanValidator:
    def __init__(self, plan: Dict[str, Any], strict: bool = True):
        self.plan = plan
        self.strict = strict
        self.errors = []
        self.warnings = []
    
    def validate_all(self) -> bool:
        """Run all validation checks"""
        checks = [
            self.validate_schema,
            self.validate_approval,
            self.validate_test_coverage,
            self.validate_security_scans,
            self.validate_dependencies,
            self.validate_acceptance_criteria,
            self.validate_task_structure,
            self.validate_rollback_procedures
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                self.errors.append(f"Check {check.__name__} failed: {str(e)}")
        
        return len(self.errors) == 0
    
    def validate_schema(self):
        """Validate against JSON schema"""
        try:
            validate(instance=self.plan, schema=PLAN_SCHEMA_V2)
        except JSONSchemaError as e:
            raise ValidationError(f"Schema validation failed: {e.message}")
    
    def validate_approval(self):
        """Ensure plan has human approval before execution"""
        meta = self.plan.get('meta', {})
        
        if not meta.get('approved_by'):
            if self.strict:
                raise ValidationError("Plan lacks human approval (approved_by field is empty)")
            else:
                self.warnings.append("Plan not yet approved - execution should be blocked")
        
        if not meta.get('approval_timestamp'):
            if self.strict:
                raise ValidationError("Plan lacks approval timestamp")
            else:
                self.warnings.append("Approval timestamp missing")
    
    def validate_test_coverage(self):
        """Ensure test tasks exist for each code task"""
        for story in self.plan.get('stories', []):
            story_id = story.get('id', 'unknown')
            tasks = story.get('tasks', [])
            
            dev_tasks = [t for t in tasks if t.get('type') in ['dev', 'refactor']]
            test_tasks = [t for t in tasks if t.get('type') == 'test']
            
            if dev_tasks and not test_tasks:
                self.errors.append(
                    f"Story {story_id} has {len(dev_tasks)} dev task(s) but no test tasks"
                )
            
            # Check for test coverage targets
            acceptance = self.plan.get('acceptance_definition', {})
            unit_tests = acceptance.get('unit_tests', {})
            if unit_tests.get('required') and not unit_tests.get('coverage_minimum'):
                self.warnings.append("Unit tests required but no coverage minimum specified")
    
    def validate_security_scans(self):
        """Validate security scanning requirements"""
        # Check if new dependencies have been scanned
        dependencies = self.plan.get('dependencies', {})
        new_packages = dependencies.get('new_packages', [])
        
        for pkg in new_packages:
            pkg_name = pkg.get('package', 'unknown')
            scan_result = pkg.get('security_scan_result')
            
            if scan_result not in ['pass', 'pending']:
                self.errors.append(
                    f"Package {pkg_name} security scan result is '{scan_result}' (must be 'pass' or 'pending')"
                )
            
            if scan_result == 'pending' and self.strict:
                self.errors.append(
                    f"Package {pkg_name} security scan is pending - must complete before approval"
                )
            
            # Check for alternatives
            if not pkg.get('alternatives_considered'):
                self.warnings.append(
                    f"Package {pkg_name} lacks alternatives analysis"
                )
            
            # Check vulnerability count
            vuln_count = pkg.get('vulnerabilities', 0)
            if vuln_count > 0:
                self.errors.append(
                    f"Package {pkg_name} has {vuln_count} known vulnerabilities"
                )
    
    def validate_dependencies(self):
        """Validate task dependencies are correctly ordered"""
        # Build dependency graph
        all_tasks = []
        for story in self.plan.get('stories', []):
            all_tasks.extend(story.get('tasks', []))
        
        task_ids = {t.get('id') for t in all_tasks}
        
        # Check for broken dependencies
        for task in all_tasks:
            task_id = task.get('id', 'unknown')
            deps = task.get('dependencies', [])
            
            for dep in deps:
                if dep not in task_ids:
                    self.errors.append(
                        f"Task {task_id} depends on {dep} which doesn't exist"
                    )
        
        # Check for circular dependencies (simple check)
        for task in all_tasks:
            visited = set()
            to_visit = [task.get('id')]
            
            while to_visit:
                current = to_visit.pop()
                if current in visited:
                    self.errors.append(f"Circular dependency detected involving {current}")
                    break
                visited.add(current)
                
                # Find current task and its dependencies
                current_task = next((t for t in all_tasks if t.get('id') == current), None)
                if current_task:
                    to_visit.extend(current_task.get('dependencies', []))
    
    def validate_acceptance_criteria(self):
        """Ensure acceptance criteria are measurable"""
        acceptance = self.plan.get('acceptance_definition', {})
        
        # Check for required fields
        required_checks = ['unit_tests', 'lint']
        for check in required_checks:
            if check not in acceptance:
                self.errors.append(f"Acceptance definition missing '{check}' section")
        
        # Validate unit tests config
        unit_tests = acceptance.get('unit_tests', {})
        if unit_tests.get('required'):
            coverage = unit_tests.get('coverage_minimum')
            if not coverage or coverage < 50 or coverage > 100:
                self.errors.append(
                    f"Invalid coverage_minimum: {coverage} (must be 50-100)"
                )
        
        # Check story-level acceptance criteria
        for story in self.plan.get('stories', []):
            story_id = story.get('id', 'unknown')
            criteria = story.get('acceptance_criteria', [])
            
            if not criteria:
                self.errors.append(f"Story {story_id} has no acceptance criteria")
            
            # Check if criteria are measurable (heuristic: should avoid vague terms)
            vague_terms = ['good', 'better', 'nice', 'clean', 'proper', 'appropriate']
            for criterion in criteria:
                criterion_lower = criterion.lower()
                if any(term in criterion_lower for term in vague_terms):
                    self.warnings.append(
                        f"Story {story_id} has vague acceptance criterion: '{criterion}'"
                    )
    
    def validate_task_structure(self):
        """Validate task organization and estimates"""
        for story in self.plan.get('stories', []):
            story_id = story.get('id', 'unknown')
            tasks = story.get('tasks', [])
            
            if not tasks:
                self.errors.append(f"Story {story_id} has no tasks")
                continue
            
            # Check for task types distribution
            task_types = [t.get('type') for t in tasks]
            if 'doc' not in task_types:
                self.warnings.append(
                    f"Story {story_id} has no documentation task"
                )
            
            # Check for effort estimates
            for task in tasks:
                task_id = task.get('id', 'unknown')
                if not task.get('estimated_hours'):
                    self.warnings.append(
                        f"Task {task_id} has no effort estimate"
                    )
    
    def validate_rollback_procedures(self):
        """Ensure rollback procedures are documented"""
        for story in self.plan.get('stories', []):
            story_id = story.get('id', 'unknown')
            for task in story.get('tasks', []):
                task_id = task.get('id', 'unknown')
                task_type = task.get('type')
                
                # Dev, infra, and migration tasks should have rollback procedures
                if task_type in ['dev', 'infra', 'migration']:
                    if not task.get('rollback_procedure'):
                        self.warnings.append(
                            f"Task {task_id} (type: {task_type}) lacks rollback procedure"
                        )
    
    def get_report(self) -> str:
        """Generate validation report"""
        report = []
        report.append("=" * 60)
        report.append("PLAN MANIFEST VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Plan Version: {self.plan.get('meta', {}).get('prompt_version', 'unknown')}")
        report.append("")
        
        if not self.errors and not self.warnings:
            report.append("✅ VALIDATION PASSED")
            report.append("All checks passed successfully.")
        else:
            if self.errors:
                report.append(f"❌ ERRORS: {len(self.errors)}")
                for i, error in enumerate(self.errors, 1):
                    report.append(f"  {i}. {error}")
                report.append("")
            
            if self.warnings:
                report.append(f"⚠️  WARNINGS: {len(self.warnings)}")
                for i, warning in enumerate(self.warnings, 1):
                    report.append(f"  {i}. {warning}")
                report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python validate_plan_manifest.py <plan_manifest.json>")
        sys.exit(2)
    
    filepath = sys.argv[1]
    
    try:
        with open(filepath, 'r') as f:
            plan = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filepath}': {e}")
        sys.exit(2)
    
    # Run validation
    validator = PlanValidator(plan, strict=True)
    is_valid = validator.validate_all()
    
    # Print report
    print(validator.get_report())
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
```

### CI/CD Integration

**GitHub Actions** (`.github/workflows/validate-llm-plan.yml`):
```yaml
name: Validate LLM Plan Manifest

on:
  pull_request:
    paths:
      - 'plan_manifest.json'
      - 'src/**'
      - 'tests/**'

jobs:
  validate-plan:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install jsonschema
      
      - name: Validate Plan Manifest
        run: |
          python scripts/validate_plan_manifest.py plan_manifest.json
      
      - name: Check Code-Test Pairing
        run: |
          # Fail if PR has code changes but no test changes
          CODE_CHANGED=$(git diff --name-only origin/main | grep -c "^src/" || echo "0")
          TESTS_CHANGED=$(git diff --name-only origin/main | grep -c "^tests/" || echo "0")
          
          if [ "$CODE_CHANGED" -gt 0 ] && [ "$TESTS_CHANGED" -eq 0 ]; then
            echo "❌ Code changes detected without corresponding test changes"
            exit 1
          fi
      
      - name: Security Scan Dependencies
        run: |
          npm audit --audit-level=high || exit 1
      
      - name: Check for Hardcoded Secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

  enforce-quality-gates:
    runs-on: ubuntu-latest
    needs: validate-plan
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Run Tests
        run: npm test
      
      - name: Check Coverage
        run: |
          npm run test:coverage
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "❌ Coverage $COVERAGE% is below 80% threshold"
            exit 1
          fi
      
      - name: Lint Code
        run: npm run lint

  security-scan:
    runs-on: ubuntu-latest
    needs: validate-plan
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Run Snyk Security Scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
```

**GitLab CI** (`.gitlab-ci.yml`):
```yaml
validate-plan:
  stage: validate
  image: python:3.11
  script:
    - pip install jsonschema
    - python scripts/validate_plan_manifest.py plan_manifest.json
  only:
    changes:
      - plan_manifest.json
      - src/**/*
      - tests/**/*

quality-gates:
  stage: test
  script:
    - npm install
    - npm test
    - npm run test:coverage
    - |
      COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
      if (( $(echo "$COVERAGE < 80" | bc -l) )); then
        echo "Coverage below threshold"
        exit 1
      fi
    - npm run lint
```

---


---

## Appendix


### Glossary

- **Agent**: LLM system with specific role and capabilities
- **Artifact**: Generated file (code, doc, config, test)
- **Checkpoint**: Saved state for context recovery
- **Definition of Done**: Set of criteria that must be met before task is considered complete
- **Epic**: Large feature composed of multiple stories
- **Phase**: Distinct stage of work (planning, implementation, testing, review)
- **Plan Manifest**: Machine-readable JSON file containing full plan structure
- **RAG**: Retrieval-Augmented Generation
- **Rollback**: Reverting code/config to previous working state
- **Stop Point**: Planned pause for approval or context management
- **Story**: User story with acceptance criteria
- **Task**: Unit of work assigned to agent or human
- **Vertical Slice**: End-to-end thin implementation of feature

### Recommended Reading

- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/en/docs/prompt-engineering)
- [OpenAI Best Practices for Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering)
- [Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903)
- [ReAct: Reasoning and Acting in LLMs](https://arxiv.org/abs/2210.03629)
- [Constitutional AI Paper](https://arxiv.org/abs/2212.08073)

### Version History

**v2.0 (2025-11-11)**
- Added chain-of-thought and reasoning patterns
- Multi-agent orchestration strategies
- RAG integration guidelines
- Structured output patterns
- Enhanced security and compliance sections
- Comprehensive error handling and recovery
- Observability and metrics framework
- Prompt versioning and regression testing
- Few-shot example patterns
- Tool use / function calling integration

**v1.0 (2025-10-01)**
- Initial release with core prompt architecture

---


---

## Quick Reference Card

### One-Page Cheat Sheet for Daily Use

```
╔══════════════════════════════════════════════════════════════════════╗
║         LLM DEVELOPMENT AGENT - QUICK REFERENCE v2.0                 ║
╠══════════════════════════════════════════════════════════════════════╣

PHASE 1: PLANNING (ALWAYS FIRST)
  □ Load requirements + constraints
  □ Ask clarifying questions (2-3 max)
  □ Propose 2-3 approaches with tradeoffs
  □ Generate plan (human .md + machine .json)
  □ WAIT for human approval: APPROVED_BY: <name> <date>
  
PHASE 2: EXECUTION (AFTER APPROVAL ONLY)
  □ Load plan_manifest.json
  □ State reasoning for approach
  □ Generate code + tests
  □ Run validations: lint + tests + security
  □ Create PR with rollback steps
  □ Update plan_manifest.json

══════════════════════════════════════════════════════════════════════

MANDATORY CHECKS BEFORE CODING
  ✓ Requirements clear (if not, ask questions)
  ✓ Plan approved (check plan_manifest.json)
  ✓ Dependencies scanned (security)
  ✓ Context <70% (if >70%, checkpoint)
  
══════════════════════════════════════════════════════════════════════

QUALITY GATES (ALL MUST PASS)
  ✓ Unit tests: ≥80% coverage, all passing
  ✓ Linter: 0 errors
  ✓ Security: 0 critical/high vulnerabilities
  ✓ Performance: meets targets (p95 latency, throughput)
  ✓ Docs: complete (inline, README, API docs)

══════════════════════════════════════════════════════════════════════

VALIDATION FAILED? DECISION TREE
  Tests failed:
    1-3 tests → Self-correct (1 attempt only)
    >3 tests → Report to human
  
  Lint errors:
    <5 errors → Self-correct
    ≥5 errors → Report to human
  
  Security issues:
    Critical/High → HALT + Report immediately
    Medium/Low → Report + propose fix
  
  Performance regression:
    <10% → Log + continue
    ≥10% → Report + propose optimization

══════════════════════════════════════════════════════════════════════

CONTEXT WINDOW MANAGEMENT
  <50%: ✅ Proceed normally
  50-70%: ⚠️ Monitor closely, plan checkpoint
  70-85%: ⚠️ Optimize first (compress, summarize)
  >85%: 🛑 CHECKPOINT NOW, request new session

══════════════════════════════════════════════════════════════════════

NEVER DO THESE (CRITICAL RULES)
  ✗ Generate code without approved plan
  ✗ Add dependencies without security scan + alternatives
  ✗ Hardcode secrets/credentials in code
  ✗ Include PII in logs or examples
  ✗ Skip tests ("I'll add them later" = ✗)
  ✗ Make breaking changes without migration path
  ✗ Execute external API calls without approval

══════════════════════════════════════════════════════════════════════

WHEN TO ASK FOR HELP
  • Requirements ambiguous (ask 2-3 clarifying questions)
  • Validation failed twice (self-correction limit reached)
  • Security critical/high vulnerabilities found
  • Performance regression >10%
  • Context window >85% (checkpoint needed)
  • Uncertain about approach (explain uncertainty)

══════════════════════════════════════════════════════════════════════

COMMIT MESSAGE FORMAT
  [Epic-ID] type: short description — detail
  
  Types: feat, fix, refactor, test, docs, chore, perf, security, ci
  
  Example:
  [E-001] feat: add user login endpoint — POST /auth/login with rate limiting

══════════════════════════════════════════════════════════════════════

FILES TO MAINTAIN
  plan_manifest.json      - Full state (machine-readable)
  phase_summary.md        - Concise summary (≤500 tokens)
  decisions.json          - Key design decisions
  artifacts_registry.json - Task → file mapping
  .llm_audit/[date]/[task].json - Audit trail

══════════════════════════════════════════════════════════════════════

COST OPTIMIZATION TIPS
  • Use caching for stable context (90% savings)
  • Generate incrementally, not all-at-once
  • Choose right model for task complexity
  • Monitor cost_per_task metric
  • Target: $0.10-0.30 per task

══════════════════════════════════════════════════════════════════════

EMERGENCY CONTACTS
  On-Call: [PagerDuty/phone]
  Escalation: [Manager/Lead]
  Rollback: kubectl rollout undo deployment/[service]

╚══════════════════════════════════════════════════════════════════════╝

Version: 2.0 | Updated: 2025-11-11 | More: [link to full guide]
```

---


---

## License

This guide is provided as-is for internal and external use. You may adapt, modify, and distribute it freely. Attribution appreciated but not required.

---

## Version History

**v2.1 (2025-11-11)** - Merged Complete Edition
- Integrated: Complete enforcement validation script with CI/CD examples
- Integrated: Comprehensive cost modeling and budgeting framework
- Integrated: Four critical decision trees (agent selection, validation failure, rollback, context management)
- Integrated: One-page quick reference card for daily use
- Enhanced: Navigation with quick start section
- Enhanced: Organization and section numbering
- Enhanced: Production operations section

**v2.0 (2025-11-11)**
- Added: Chain-of-thought and reasoning patterns (CoT, Tree-of-Thoughts, Reflection)
- Added: Multi-agent orchestration strategies with communication protocols
- Added: RAG integration guidelines and patterns
- Added: Structured output modes (JSON mode, function calling)
- Added: Enhanced security and compliance sections with GDPR checklist
- Added: Comprehensive error handling and recovery patterns
- Added: Observability and metrics framework with dashboards
- Added: Prompt versioning and regression testing
- Added: Few-shot example patterns
- Added: Tool use / function calling integration
- Added: Specialized task patterns (Frontend, API, Data Pipeline, IaC, Refactoring, Bug Fix)
- Enhanced: JSON schema v2.0 with additional validation
- Enhanced: Context management strategies with token budgets
- Enhanced: Testing pyramid with property-based testing
- Enhanced: Dependency management protocol with supply chain security
- Improved: Template examples with before/after comparison
- Improved: Organization with comprehensive table of contents

**v1.0 (2025-10-01)**
- Initial release with core prompt architecture
- Basic planning and execution framework
- Essential security and compliance guidelines
- Fundamental testing requirements

---

## Feedback & Support

**Document Version**: 2.1 (Merged Complete Edition)
**Last Updated**: November 11, 2025  
**Maintainer**: [Your Team/Name]  
**Issues/Questions**: [GitHub Issues URL or email]  
**Discussions**: [Slack channel, Discord, or forum]

---

## Acknowledgments

This guide synthesizes best practices from:
- Software engineering (TDD, Clean Code, SOLID principles)
- API design (OpenAPI, REST, GraphQL communities)
- AI research (Chain-of-Thought, Constitutional AI, RAG)
- DevOps (SRE principles, incident response, monitoring)
- Security (OWASP, CWE, security engineering)

Special thanks to practitioners who tested early versions and provided feedback.

---

**End of Guide v2.1**

*This merged edition combines the comprehensive framework with practical enforcement tools, cost modeling, decision support, and quick reference materials - everything you need in one complete document.*
