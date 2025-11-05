# LLM Parameter Flow - State to Prompts

**Version**: 1.2 (M9)
**Date**: November 3, 2025
**Status**: Living Document

---

## Overview

This document maps how system state flows from various managers through to prompts sent to Qwen (local LLM) for validation, quality assessment, and decision-making.

**Key Insight**: The orchestrator uses Qwen for **validation and oversight**, not task execution. Claude Code executes tasks, Qwen validates the results.

### 📊 Critical Review Available

**A comprehensive analysis of parameter effectiveness is available**: See [PARAMETER_REVIEW_ANALYSIS.md](./PARAMETER_REVIEW_ANALYSIS.md) for:
- **3 Critical Issues** requiring immediate attention
- **8 Optimization Opportunities** with expected impact metrics
- **Implementation roadmap** with prioritized phases
- **Measurement plan** to track improvement

**Quick Summary of Key Findings**:
- ⚠️ **Issue 1**: Context priorities optimized for task execution, not validation (HIGH IMPACT)
- ⚠️ **Issue 2**: M9 parameters (dependencies, git) underutilized in templates (MEDIUM-HIGH IMPACT)
- ⚠️ **Issue 3**: No feedback loop to measure which parameters help Qwen make better decisions (HIGH IMPACT)
- 📈 **Expected Impact of Fixes**: 15-25% improvement in validation accuracy

**Recommendation**: Review the analysis document before making template changes.

---

## Table of Contents

1. [High-Level Flow](#high-level-flow)
2. [State Managers Overview](#state-managers-overview)
3. [Parameter Flow Diagrams](#parameter-flow-diagrams)
4. [Prompt Templates & Parameters](#prompt-templates--parameters)
5. [Context Building Process](#context-building-process)
6. [LLM Call Patterns](#llm-call-patterns)
7. [Parameter Reference](#parameter-reference)
8. [Next Steps & Recommendations](#next-steps--recommendations)

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR MAIN LOOP                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  StateManager    │───▶│ ContextManager   │───▶│PromptGenerator  │
│  (Task, Project) │    │ (Build Context)  │    │ (Jinja2 Render) │
└──────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ DependencyResolver    │ GitManager       │    │  PROMPT TEXT    │
│ (Task Relations) │    │ (File Changes)   │    │  (Final String) │
└──────────────────┘    └──────────────────┘    └─────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  LocalLLMInterface
                                                  │  (Qwen via Ollama)
                                                  └─────────────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ QualityController
                                                  │ DecisionEngine  │
                                                  │ ConfidenceScorer│
                                                  └─────────────────┘
```

---

## State Managers Overview

### 1. StateManager (`src/core/state.py`)

**Purpose**: Single source of truth for all system state (tasks, projects, iterations)

**Key Data Provided**:
```python
{
    'task_id': int,
    'task_title': str,
    'task_description': str,
    'task_priority': int,
    'task_status': TaskStatus,
    'task_dependencies': List[int],
    'project_id': int,
    'project_name': str,
    'working_directory': str,
    'project_goals': str,
    'iteration_count': int,
    'previous_iterations': List[Dict],
    'last_output': str,
    'error_history': List[Dict]
}
```

**When Used**: Every LLM call (provides core context)

---

### 2. ContextManager (`src/utils/context_manager.py`)

**Purpose**: Prioritize and fit information within token limits

**Key Functionality**:
- Prioritizes information by importance
- Summarizes large content
- Manages token budget
- Caches built contexts

**Priority Order** (most to least important):
1. `current_task_description` - What we're working on NOW
2. `recent_errors` - Problems to avoid/fix
3. `active_code_files` - Current working files
4. `task_dependencies` - What depends on what (M9)
5. `project_goals` - High-level objectives
6. `conversation_history` - Recent exchanges
7. `documentation` - Reference materials

**Parameters**:
```python
{
    'max_tokens': 100000,          # Total budget
    'summarization_threshold': 50000,  # When to summarize
    'compression_ratio': 0.3,      # How much to compress
    'items': List[ContextItem]     # Prioritized content
}
```

---

### 3. DependencyResolver (`src/orchestration/dependency_resolver.py`) [M9]

**Purpose**: Understand task relationships and execution order

**Key Data Provided**:
```python
{
    'task_dependencies': List[int],  # Tasks this depends on
    'dependent_tasks': List[int],    # Tasks depending on this
    'execution_order': List[int],    # Correct execution sequence
    'blocked_tasks': List[int],      # Tasks waiting on dependencies
    'dependency_graph': str          # ASCII visualization
}
```

**When Used**:
- Task execution planning
- Validation (check if prerequisites met)
- Error analysis (was dependency issue?)

---

### 4. GitManager (`src/utils/git_manager.py`) [M9]

**Purpose**: Track file changes and version control context

**Key Data Provided**:
```python
{
    'current_branch': str,
    'git_status': str,               # Modified/added files
    'file_changes': List[FileChange],  # Detailed change list
    'commit_history': List[Commit],  # Recent commits
    'uncommitted_changes': bool,
    'pr_status': Optional[str]       # If PR created
}
```

**When Used**:
- Validation (check what files changed)
- Commit message generation (uses Qwen!)
- Rollback decision (was change problematic?)

---

### 5. PromptGenerator (`src/llm/prompt_generator.py`)

**Purpose**: Convert structured data into natural language prompts

**Process**:
1. Load Jinja2 template (from `config/prompt_templates.yaml`)
2. Inject parameters from managers
3. Apply custom filters (truncate, summarize, format_code)
4. Render final prompt text
5. Validate token budget
6. Cache for reuse

**Custom Filters**:
- `truncate(n)` - Limit to n characters
- `summarize(max_tokens=n)` - Use LLM to summarize
- `format_code` - Apply syntax highlighting
- `join(sep)` - Join list with separator

---

### 6. QualityController (`src/orchestration/quality_controller.py`)

**Purpose**: Validate Claude Code's output using Qwen

**Validation Stages**:
```
Stage 1: Syntax Check     (fast, regex/AST)
    ↓
Stage 2: Requirements     (LLM: did it meet criteria?)
    ↓
Stage 3: Quality          (LLM: is it good code?)
    ↓
Stage 4: Testing          (run tests if available)
```

**LLM Calls Made**:
- Stage 2: `validation` template
- Stage 3: `quality_check` template

**Parameters Sent to Qwen**:
```python
{
    'task_title': str,
    'task_description': str,
    'expected_outcome': str,
    'work_output': str,           # Claude Code's response
    'file_changes': List[Dict],
    'test_results': Optional[str],
    'validation_criteria': List[str],
    'previous_feedback': List[str]
}
```

---

### 7. DecisionEngine (`src/orchestration/decision_engine.py`)

**Purpose**: Decide what to do next based on validation results

**LLM Calls Made**:
- `error_analysis` template (when failure occurs)
- `decision_recommendation` template (for complex scenarios)

**Parameters Sent to Qwen**:
```python
{
    'validation_result': Dict,     # From QualityController
    'confidence_score': float,     # From ConfidenceScorer
    'iteration_count': int,
    'max_iterations': int,
    'error_history': List[Dict],
    'task_context': Dict,
    'available_actions': List[str]  # proceed/retry/clarify/escalate
}
```

**Decision Tree**:
```
Is Valid? ──YES──▶ Quality > Threshold? ──YES──▶ PROCEED
    │                     │
   NO                    NO
    │                     │
    ▼                     ▼
Max Retries? ──NO──▶ RETRY (with feedback)
    │
   YES
    │
    ▼
Escalate? ──YES──▶ HUMAN_REVIEW
    │
   NO
    │
    ▼
  FAIL
```

---

## Parameter Flow Diagrams

### Task Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    TASK EXECUTION REQUEST                        │
│  User: "Execute task 5"                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  StateManager    │
                    │  get_task(5)     │
                    └──────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Task Object:       │
                    │ - id: 5            │
                    │ - title: "Auth"    │
                    │ - description: ... │
                    │ - priority: 8      │
                    │ - dependencies: [3]│
                    └────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
    ┌───────────────┐  ┌────────────┐  ┌──────────────┐
    │DependencyResolver GitManager  │  │ContextManager│
    │check_ready(5) │  │get_status()│  │build_context()│
    └───────────────┘  └────────────┘  └──────────────┘
            │                  │              │
            └─────────┬────────┴──────────────┘
                      ▼
            ┌──────────────────┐
            │ PromptGenerator  │
            │ generate_prompt( │
            │   'task_execution'│
            │   {all params}   │
            │ )                │
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ RENDERED PROMPT: │
            │                  │
            │ You are working  │
            │ on task "Auth"   │
            │ for project...   │
            │                  │
            │ Dependencies:    │
            │ - Task 3 ✓ done  │
            │                  │
            │ Files changed:   │
            │ - auth.py (M)    │
            │                  │
            │ Recent errors:   │
            │ (none)           │
            │                  │
            │ Please implement │
            │ ...              │
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  Claude Code CLI │
            │  (Task Execution)│
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │   Agent Output   │
            │ "Created auth.py"│
            │ "Added JWT..."   │
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ QualityController│
            │ validate_output()│
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ VALIDATION PROMPT│
            │ to Qwen:         │
            │                  │
            │ Task: "Auth"     │
            │ Output: ...      │
            │ Files: auth.py   │
            │                  │
            │ Validate against:│
            │ - JWT tokens     │
            │ - Login endpoint │
            │ ...              │
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ Qwen Response    │
            │ {                │
            │   is_valid: true │
            │   score: 0.85    │
            │   issues: []     │
            │ }                │
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ DecisionEngine   │
            │ decide_next()    │
            │ → PROCEED        │
            └──────────────────┘
```

---

### Validation Flow (Quality Check)

```
┌──────────────────────────────────────────────────────────────┐
│             Claude Code completes task                        │
│  Output: "Implemented JWT authentication in auth.py"         │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │QualityController │
                  │validate_output() │
                  └──────────────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Stage 1 │    │  Stage 2 │    │  Stage 3 │
    │  Syntax  │───▶│Requirements───▶│ Quality  │
    │ (local)  │    │  (Qwen)  │    │  (Qwen)  │
    └──────────┘    └──────────┘    └──────────┘
         │                 │                │
         │                 │                │
    Parameters      Parameters         Parameters
    Gathered        Gathered           Gathered
         │                 │                │
         └────────┬────────┴────────────────┘
                  ▼
        ┌──────────────────┐
        │ PromptGenerator  │
        │ template:        │
        │ 'validation'     │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────────────────────┐
        │ VALIDATION PROMPT               │
        │                                 │
        │ Task: "Implement JWT auth"      │
        │ Description: User authentication│
        │ Expected: JWT tokens, endpoints │
        │                                 │
        │ Work Submitted:                 │
        │ --------------------------------│
        │ Created auth.py with:           │
        │ - JWTManager class              │
        │ - /login endpoint               │
        │ - Token generation              │
        │ - Token validation              │
        │                                 │
        │ Files Changed:                  │
        │ - auth.py (new, 245 lines)      │
        │ - routes.py (modified, +12)     │
        │                                 │
        │ Test Results:                   │
        │ PASSED: test_jwt_generation     │
        │ PASSED: test_login_endpoint     │
        │ PASSED: test_token_validation   │
        │                                 │
        │ Validation Criteria:            │
        │ - Uses industry-standard JWT    │
        │ - Implements login endpoint     │
        │ - Validates tokens properly     │
        │ - Has error handling            │
        │ - Includes tests                │
        │                                 │
        │ Respond with JSON:              │
        │ {                               │
        │   "is_valid": bool,             │
        │   "quality_score": float,       │
        │   "issues": [...],              │
        │   "suggestions": [...]          │
        │ }                               │
        └──────────────────────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  Qwen (Ollama)   │
        │  Analyzes code   │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────────────────────┐
        │ QWEN RESPONSE                   │
        │ {                               │
        │   "is_valid": true,             │
        │   "quality_score": 0.92,        │
        │   "issues": [],                 │
        │   "suggestions": [              │
        │     "Add rate limiting",        │
        │     "Add refresh token support" │
        │   ]                             │
        │ }                               │
        └──────────────────────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ DecisionEngine   │
        │ Score >= 0.70?   │
        │ YES → PROCEED    │
        └──────────────────┘
```

---

### Error Analysis Flow

```
┌──────────────────────────────────────────────────────────────┐
│             Claude Code encounters error                      │
│  Error: ImportError: No module named 'jwt'                   │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  StateManager    │
                  │  record_error()  │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ DecisionEngine   │
                  │ analyze_error()  │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ PromptGenerator  │
                  │ 'error_analysis' │
                  └──────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────┐
        │ ERROR ANALYSIS PROMPT           │
        │                                 │
        │ Task: "Implement JWT auth"      │
        │                                 │
        │ Error Details:                  │
        │ Type: ImportError               │
        │ Message: No module named 'jwt'  │
        │ Timestamp: 2025-11-03 14:23:10  │
        │                                 │
        │ Stack Trace:                    │
        │ File "auth.py", line 1          │
        │   import jwt                    │
        │ ImportError: No module 'jwt'    │
        │                                 │
        │ Context:                        │
        │ - Iteration: 1 of 5             │
        │ - Previous attempts: 0          │
        │ - Similar past errors: 0        │
        │                                 │
        │ Files Involved:                 │
        │ - auth.py (newly created)       │
        │                                 │
        │ Project Environment:            │
        │ - Python 3.12                   │
        │ - requirements.txt exists       │
        │ - venv not activated?           │
        │                                 │
        │ Analysis Request:               │
        │ 1. Is this a recoverable error? │
        │ 2. What caused it?              │
        │ 3. How to fix it?               │
        │ 4. Should we retry or escalate? │
        │                                 │
        │ Respond with JSON:              │
        │ {                               │
        │   "error_category": str,        │
        │   "is_recoverable": bool,       │
        │   "root_cause": str,            │
        │   "fix_suggestion": str,        │
        │   "retry_recommended": bool     │
        │ }                               │
        └──────────────────────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  Qwen (Ollama)   │
        │  Analyzes error  │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────────────────────┐
        │ QWEN RESPONSE                   │
        │ {                               │
        │   "error_category": "dependency"│
        │   "is_recoverable": true,       │
        │   "root_cause": "PyJWT package  │
        │                  not installed",│
        │   "fix_suggestion": "Add PyJWT  │
        │      to requirements.txt and    │
        │      run pip install",          │
        │   "retry_recommended": true     │
        │ }                               │
        └──────────────────────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ DecisionEngine   │
        │ Action: RETRY    │
        │ with feedback    │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────────────────────┐
        │ Enhanced Prompt to Claude Code: │
        │                                 │
        │ Previous attempt failed:        │
        │ - Missing PyJWT dependency      │
        │                                 │
        │ Please:                         │
        │ 1. Add PyJWT to requirements.txt│
        │ 2. Install with pip install     │
        │ 3. Then import jwt in auth.py   │
        └──────────────────────────────────┘
```

---

## Prompt Templates & Parameters

### Template: `task_execution`

**Purpose**: Instruct Claude Code on what to implement

**Required Parameters**:
```python
{
    'project_name': str,           # From StateManager
    'task_id': int,                # From StateManager
    'task_title': str,             # From StateManager
    'task_description': str,       # From StateManager
    'working_directory': str,      # From StateManager
}
```

**Optional Parameters**:
```python
{
    'task_priority': int,          # From StateManager (default: 5)
    'task_dependencies': List[str],  # From DependencyResolver (M9)
    'project_goals': str,          # From StateManager
    'current_files': List[Dict],   # From GitManager
    'recent_errors': List[Dict],   # From StateManager
    'conversation_history': str,   # From ContextManager
    'examples': List[Dict],        # From pattern learning
    'instructions': str,           # Custom instructions
}
```

**Example Rendered**:
```
You are working on the following task for the "Obra" project.

## Task Information
**Task ID**: 5
**Title**: Implement user authentication
**Description**: Add JWT-based authentication with login/logout endpoints
**Priority**: 8
**Dependencies**: Task 3 (Database setup)

## Project Context
Working Directory: /home/user/obra
Project Goals:
Build an orchestrator for managing Claude Code with local LLM oversight.

## Current Active Files
- src/auth.py (0 bytes, last modified: 2025-11-03 14:20:00)
- src/routes.py (1234 bytes, last modified: 2025-11-03 14:15:00)

## Instructions
Please implement JWT authentication with:
- User login endpoint
- Token generation and validation
- Secure password hashing
- Logout functionality

Please complete this task efficiently and report your progress.
```

---

### Template: `validation`

**Purpose**: Ask Qwen to validate Claude Code's work

**Required Parameters**:
```python
{
    'task_title': str,
    'task_description': str,
    'expected_outcome': str,
    'work_output': str,            # Claude Code's response
    'validation_criteria': List[str]
}
```

**Optional Parameters**:
```python
{
    'file_changes': List[Dict],    # From GitManager
    'test_results': str,           # From test execution
}
```

---

### Template: `error_analysis`

**Purpose**: Ask Qwen to analyze why something failed

**Required Parameters**:
```python
{
    'error_type': str,
    'error_message': str,
    'error_timestamp': str,
    'task_context': Dict
}
```

**Optional Parameters**:
```python
{
    'stack_trace': str,
    'files_involved': List[str],
    'iteration_count': int,
    'previous_attempts': List[Dict],
    'environment_info': Dict
}
```

---

### Template: `quality_check`

**Purpose**: Ask Qwen to assess code quality

**Required Parameters**:
```python
{
    'code_snippet': str,
    'language': str,
    'quality_criteria': List[str]
}
```

**Optional Parameters**:
```python
{
    'complexity_score': float,
    'test_coverage': float,
    'style_issues': List[str]
}
```

---

## Context Building Process

### ContextManager Algorithm

```
1. GATHER all available context items
   └─ StateManager (task, project, iterations)
   └─ DependencyResolver (task relationships)
   └─ GitManager (file changes)
   └─ Previous LLM responses
   └─ Error history

2. PRIORITIZE items
   └─ Calculate priority score:
       score = (recency × 0.3) +
               (relevance × 0.4) +
               (importance × 0.2) +
               (size_efficiency × 0.1)

3. SORT by priority (highest first)

4. FIT within token budget
   └─ Start with highest priority
   └─ Add items until budget reached
   └─ If item too large:
       ├─ Summarize if possible (use Qwen)
       └─ Truncate if necessary

5. ASSEMBLE final context
   └─ Inject into template
   └─ Render with Jinja2

6. CACHE result
   └─ Key: hash(template + params)
   └─ Reuse for identical contexts
```

### Token Budget Example

```
Max Tokens: 100,000

Allocation:
├─ Task description:      1,000 tokens  (always included)
├─ Recent errors:         2,000 tokens  (high priority)
├─ Active files:          5,000 tokens  (medium priority)
├─ Dependencies:            500 tokens  (M9 - medium priority)
├─ Project goals:         1,500 tokens  (medium priority)
├─ Conversation history: 20,000 tokens  (summarized from 50,000)
└─ Documentation:        10,000 tokens  (low priority, truncated)

Total Used: 40,000 tokens
Remaining: 60,000 tokens (buffer)
```

---

## LLM Call Patterns

### When Qwen is Called

| Scenario | Template | Frequency | Purpose |
|----------|----------|-----------|---------|
| **Task Validation** | `validation` | Every task completion | Verify Claude Code's work |
| **Quality Check** | `quality_check` | Every task completion | Assess code quality |
| **Error Analysis** | `error_analysis` | On failure | Understand what went wrong |
| **Decision Help** | `decision_recommendation` | Complex scenarios | Choose next action |
| **Commit Messages** | `commit_message` (M9) | Per commit | Generate semantic messages |
| **Summarization** | (internal) | As needed | Compress large context |

### Qwen Response Formats

All Qwen responses are requested in **JSON format** for easy parsing:

```json
{
    "is_valid": true,
    "quality_score": 0.85,
    "confidence": 0.90,
    "issues": [
        "Missing error handling in login function",
        "Password validation could be stronger"
    ],
    "suggestions": [
        "Add try-catch around JWT verification",
        "Implement password complexity requirements"
    ],
    "reasoning": "The implementation correctly uses JWT and provides basic auth functionality, but could benefit from improved error handling and validation."
}
```

---

## Parameter Reference

### Complete Parameter Mapping

| Parameter | Source | Used In Templates | Type | Required |
|-----------|--------|-------------------|------|----------|
| **task_id** | StateManager | task_execution, validation | int | Yes |
| **task_title** | StateManager | task_execution, validation, error_analysis | str | Yes |
| **task_description** | StateManager | task_execution, validation | str | Yes |
| **task_priority** | StateManager | task_execution | int | No (default: 5) |
| **task_status** | StateManager | error_analysis, decision | TaskStatus | No |
| **task_dependencies** | DependencyResolver (M9) | task_execution | List[int] | No |
| **project_id** | StateManager | (internal routing) | int | Yes |
| **project_name** | StateManager | task_execution | str | Yes |
| **project_goals** | StateManager | task_execution | str | No |
| **working_directory** | StateManager | task_execution, error_analysis | str | Yes |
| **iteration_count** | StateManager | error_analysis, decision | int | Yes |
| **max_iterations** | Config | decision | int | Yes |
| **current_files** | GitManager (M9) | task_execution, validation | List[Dict] | No |
| **file_changes** | GitManager (M9) | validation, error_analysis | List[Dict] | No |
| **git_status** | GitManager (M9) | validation | str | No |
| **recent_errors** | StateManager | task_execution, error_analysis | List[Dict] | No |
| **error_type** | Exception | error_analysis | str | Yes (when error) |
| **error_message** | Exception | error_analysis | str | Yes (when error) |
| **stack_trace** | Exception | error_analysis | str | No |
| **work_output** | Agent Response | validation, quality_check | str | Yes |
| **test_results** | Test Execution | validation | str | No |
| **validation_criteria** | Config/Task | validation | List[str] | Yes |
| **quality_criteria** | Config | quality_check | List[str] | Yes |
| **conversation_history** | ContextManager | task_execution | str | No |
| **examples** | Pattern Learning | task_execution | List[Dict] | No |
| **expected_outcome** | Task | validation | str | Yes |
| **confidence_score** | ConfidenceScorer | decision | float | Yes |
| **validation_result** | QualityController | decision | Dict | Yes |
| **available_actions** | DecisionEngine | decision | List[str] | Yes |

---

## Visual Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARAMETER FLOW SUMMARY                        │
└─────────────────────────────────────────────────────────────────┘

STATE MANAGERS              PARAMETERS              QWEN PROMPTS
═══════════════            ══════════════          ═════════════

StateManager ───────────▶  task_id              ─┐
                          task_title             │
                          task_description       │
                          project_name           ├─▶ task_execution
                          working_directory      │
                          project_goals          │
                          iteration_count        │
                          error_history         ─┘

DependencyResolver ─────▶  task_dependencies    ─┐
(M9)                      execution_order        ├─▶ task_execution
                          blocked_tasks         ─┘   validation

GitManager ─────────────▶  current_files        ─┐
(M9)                      file_changes           │
                          git_status             ├─▶ validation
                          commit_history        ─┘   quality_check

ContextManager ─────────▶  conversation_history ─┐
                          summarized_docs        ├─▶ (all prompts)
                          examples              ─┘

Exception Handler ──────▶  error_type           ─┐
                          error_message          │
                          stack_trace            ├─▶ error_analysis
                          files_involved        ─┘

QualityController ──────▶  validation_result    ─┐
                          quality_score          │
                          issues                 ├─▶ decision
                          suggestions           ─┘

ConfidenceScorer ───────▶  confidence_score     ─▶  decision


PROMPT TEMPLATES
════════════════

┌──────────────────┐
│ task_execution   │ → Claude Code (what to do)
└──────────────────┘

┌──────────────────┐
│ validation       │ → Qwen (is work valid?)
└──────────────────┘

┌──────────────────┐
│ quality_check    │ → Qwen (is work good?)
└──────────────────┘

┌──────────────────┐
│ error_analysis   │ → Qwen (why did it fail?)
└──────────────────┘

┌──────────────────┐
│ decision         │ → Qwen (what should we do?)
└──────────────────┘
```

---

## Next Steps & Recommendations

### 📋 Critical Analysis Completed

A **detailed critical review** of parameter effectiveness has been completed and documented in:
**[PARAMETER_REVIEW_ANALYSIS.md](./PARAMETER_REVIEW_ANALYSIS.md)**

This analysis identifies:
- **3 Critical Issues** that impact validation accuracy
- **8 Optimization Opportunities** with implementation priorities
- **4-Phase Implementation Roadmap** with timeline estimates
- **Measurement Plan** to track improvements

### 🎯 Immediate Action Items (Phase 1)

**Priority 1: Fix Context Priority Mismatch**
- **Issue**: Current priorities optimized for task execution, not validation
- **Impact**: High - Qwen receives suboptimal context
- **Fix**: Implement template-specific priority orders
- **Files**: `src/utils/context_manager.py`, `src/llm/prompt_generator.py`
- **Timeline**: 1-2 weeks

**Priority 2: Enhance M9 Parameters in Templates**
- **Issue**: Dependencies and git tracking underutilized in prompts
- **Impact**: Medium-High - Missing critical validation context
- **Fix**: Add dependency status, git diffs, retry context to templates
- **Files**: `config/prompt_templates.yaml`, `src/orchestration/quality_controller.py`
- **Timeline**: 1-2 weeks

**Priority 3: Structured Output Enforcement**
- **Issue**: JSON parsing failures when Qwen adds preamble
- **Impact**: Medium - Causes validation errors
- **Fix**: Stronger JSON constraints + fallback extraction
- **Files**: `config/prompt_templates.yaml`, `src/orchestration/quality_controller.py`
- **Timeline**: 3-5 days

### 📊 Measurement & Tracking (Phase 2)

**Priority 4: Parameter Effectiveness Tracking**
- **Goal**: Measure which parameters help Qwen make accurate decisions
- **Implementation**: Add `ParameterEffectiveness` database model + logging
- **Files**: `src/core/models.py`, `src/core/state.py`, `src/orchestration/quality_controller.py`
- **Timeline**: 2-3 weeks

**Priority 5: Confidence Calibration**
- **Goal**: Adjust Qwen's confidence scores based on actual outcomes
- **Implementation**: Track prediction vs. actual, apply calibration curve
- **Files**: `src/utils/confidence_scorer.py`, `src/core/state.py`
- **Timeline**: 1-2 weeks

### 🚀 Expected Impact

Implementing Phase 1 + Phase 2 fixes should result in:
- 📈 **15-25% improvement** in validation accuracy
- 📈 **20% better token utilization** (less truncation/waste)
- 📈 **30-50% fewer parsing errors** (structured output)
- 📈 **Continuous improvement** via measurement infrastructure

### 🔬 Questions to Monitor

As we implement fixes, track:

1. **Validation Accuracy**:
   - % of Qwen validations that match human review
   - False positive rate (marked valid but wrong)
   - False negative rate (marked invalid but correct)

2. **Token Efficiency**:
   - Average tokens per prompt by template type
   - % of prompts hitting token limit
   - Which sections get truncated most often

3. **Parameter Effectiveness**:
   - Which parameters correlate with accurate validation?
   - Which parameters are truncated most?
   - Are M9 parameters (dependencies, git) useful?

4. **Decision Quality**:
   - % of tasks requiring human intervention (breakpoints)
   - % of retries that succeed after Qwen analysis
   - Average attempts per task completion

### 📚 Reference Documents

- **This Document**: High-level parameter flow mapping
- **[PARAMETER_REVIEW_ANALYSIS.md](./PARAMETER_REVIEW_ANALYSIS.md)**: Critical analysis + recommendations
- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Overall system architecture
- **[TEST_GUIDELINES.md](../development/TEST_GUIDELINES.md)**: Testing best practices

---

**Maintained by**: Obra Development Team
**Last Updated**: November 3, 2025
**Review Status**: ✅ Analysis Complete - Ready for Phase 1 Implementation
**Version**: 1.0 (Post-M9)
