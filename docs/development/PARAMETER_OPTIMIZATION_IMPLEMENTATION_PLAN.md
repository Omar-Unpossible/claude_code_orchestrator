# Parameter Optimization Implementation Plan

**Format**: Machine-Optimized for LLM Execution
**Status**: Ready for Implementation
**Date**: 2025-11-03

---

## PHASE_1: CRITICAL_FIXES

### TASK_1.1: Template-Specific Context Priorities

**ID**: TASK_1.1
**Priority**: CRITICAL
**Estimated_Duration**: 4-6 hours
**Dependencies**: []

**Objective**: Implement template-specific context priority orders to optimize context for different use cases (task execution vs validation vs error analysis).

**Current_State**:
- File: `src/utils/context_manager.py`
- Lines: 50-58
- Single priority order used for all templates
- Priority order optimized for task execution only

**Target_State**:
- Multiple priority orders indexed by template name
- ContextManager accepts template_name parameter
- PromptGenerator passes template_name to ContextManager
- Each template gets appropriate priority order

**Implementation_Steps**:

STEP_1.1.1: Modify ContextManager
  File: src/utils/context_manager.py
  Action: REPLACE
  Location: Lines 50-58
  Old_Code: |
    DEFAULT_PRIORITY_ORDER = [
        'current_task_description',
        'recent_errors',
        'active_code_files',
        'task_dependencies',
        'project_goals',
        'conversation_history',
        'documentation'
    ]
  New_Code: |
    DEFAULT_PRIORITY_ORDER = [
        'current_task_description',
        'recent_errors',
        'active_code_files',
        'task_dependencies',
        'project_goals',
        'conversation_history',
        'documentation'
    ]

    PRIORITY_BY_TEMPLATE = {
        'task_execution': [
            'current_task_description',
            'recent_errors',
            'active_code_files',
            'task_dependencies',
            'project_goals',
            'conversation_history'
        ],
        'validation': [
            'work_output',
            'expected_outcome',
            'file_changes',
            'test_results',
            'task_description',
            'validation_criteria'
        ],
        'error_analysis': [
            'error_message',
            'error_stacktrace',
            'agent_output',
            'recent_errors',
            'task_context',
            'recent_interactions'
        ],
        'decision': [
            'validation_result',
            'agent_response',
            'task_status',
            'attempt_count',
            'project_state',
            'recent_breakpoints'
        ],
        'code_review': [
            'file_changes',
            'work_output',
            'task_description',
            'project_standards',
            'test_results'
        ]
    }

STEP_1.1.2: Update build_context signature
  File: src/utils/context_manager.py
  Action: MODIFY
  Location: Lines 89-94
  Changes:
    - Add template_name parameter with default None
    - Use PRIORITY_BY_TEMPLATE[template_name] if provided
    - Fall back to priority_order parameter or DEFAULT_PRIORITY_ORDER
  Signature_Before: |
    def build_context(
        self,
        items: List[Dict[str, Any]],
        max_tokens: int,
        priority_order: Optional[List[str]] = None
    ) -> str:
  Signature_After: |
    def build_context(
        self,
        items: List[Dict[str, Any]],
        max_tokens: int,
        priority_order: Optional[List[str]] = None,
        template_name: Optional[str] = None
    ) -> str:
  Implementation: |
    # Inside build_context, around line 117
    # Determine priority order
    if template_name and template_name in self.PRIORITY_BY_TEMPLATE:
        priority_order = self.PRIORITY_BY_TEMPLATE[template_name]
    elif priority_order is None:
        priority_order = self.DEFAULT_PRIORITY_ORDER

STEP_1.1.3: Update PromptGenerator to pass template_name
  File: src/llm/prompt_generator.py
  Action: MODIFY
  Location: inject_context method (lines 521-604)
  Changes:
    - Pass template_name to ContextManager.build_context
    - Note: inject_context doesn't currently use ContextManager, needs refactor
  Implementation: |
    # If inject_context uses ContextManager in future:
    context = self.context_manager.build_context(
        items=context_items,
        max_tokens=available_tokens,
        template_name=template_name  # ADD THIS
    )

STEP_1.1.4: Update QualityController validation calls
  File: src/orchestration/quality_controller.py
  Action: MODIFY
  Location: validate_response method
  Changes:
    - When building context for validation, specify template_name='validation'
  Search_Pattern: "build_context|inject_context"
  Implementation_Note: |
    # Find where context is built for validation prompts
    # Add template_name='validation' parameter

**Validation_Criteria**:
- [ ] ContextManager has PRIORITY_BY_TEMPLATE dict
- [ ] build_context accepts template_name parameter
- [ ] Each template name in PRIORITY_BY_TEMPLATE has appropriate order
- [ ] Unit test: build_context with template_name='validation' uses validation priority
- [ ] Unit test: build_context with template_name='task_execution' uses task priority
- [ ] Unit test: build_context with unknown template_name falls back to default
- [ ] Integration test: QualityController validation uses correct priority

**Test_Cases**:
```python
# test_context_manager.py - Add these tests

def test_template_specific_priorities(context_manager):
    """Test that template-specific priorities are used."""
    items = [
        {'type': 'work_output', 'content': 'Output', 'priority': 5},
        {'type': 'task_description', 'content': 'Task', 'priority': 5},
        {'type': 'file_changes', 'content': 'Changes', 'priority': 5}
    ]

    # Validation template should prioritize work_output
    validation_context = context_manager.build_context(
        items, max_tokens=1000, template_name='validation'
    )
    assert validation_context.index('Output') < validation_context.index('Task')

    # Task execution template should prioritize task_description
    task_context = context_manager.build_context(
        items, max_tokens=1000, template_name='task_execution'
    )
    # Would need current_task_description type for proper test
    assert 'Task' in task_context

def test_fallback_to_default_priority(context_manager):
    """Test fallback when template_name not recognized."""
    items = [{'type': 'current_task_description', 'content': 'Test', 'priority': 5}]

    context = context_manager.build_context(
        items, max_tokens=1000, template_name='unknown_template'
    )
    assert 'Test' in context  # Should use DEFAULT_PRIORITY_ORDER
```

**Success_Metrics**:
- Metric: Context priority order differs by template type
- Metric: Validation template receives work_output before task_description
- Metric: No regression in existing tests
- Target: 100% test pass rate

---

### TASK_1.2: Enhanced M9 Parameters in Templates

**ID**: TASK_1.2
**Priority**: HIGH
**Estimated_Duration**: 6-8 hours
**Dependencies**: []

**Objective**: Enhance prompt templates to fully utilize M9 features (dependencies, git tracking, retry logic).

**Files_Modified**:
- config/prompt_templates.yaml
- src/orchestration/quality_controller.py
- src/llm/prompt_generator.py

**Implementation_Steps**:

STEP_1.2.1: Enhance task_execution template
  File: config/prompt_templates.yaml
  Action: REPLACE
  Location: Lines 5-57 (task_execution section)
  Enhancement_Areas:
    - Add dependency status section
    - Add retry context section
    - Add git context section
  New_Template: |
    task_execution: |
      You are working on the following task for the "{{ project_name }}" project.

      ## Task Information
      **Task ID**: {{ task_id }}
      **Title**: {{ task_title }}
      **Description**: {{ task_description }}
      **Priority**: {{ task_priority | default(5) }}
      {% if task_dependencies %}

      ### Dependencies ({{ task_dependencies | length }})
      This task depends on the following tasks completing first:
      {% for dep in task_dependencies_detailed %}
      - **Task #{{ dep.id }}**: {{ dep.title }}
        - Status: {{ dep.status }}
        - Completion: {{ dep.completion_percentage }}%
        {% if dep.output %}
        - Output Summary: {{ dep.output | truncate(200) }}
        {% endif %}
        {% if dep.blocking_reason %}
        - ⚠️  Blocking: {{ dep.blocking_reason }}
        {% endif %}
      {% endfor %}
      {% endif %}

      {% if retry_context %}
      ## 🔄 Retry Information
      **Attempt**: {{ retry_context.attempt_number }} of {{ retry_context.max_attempts }}
      **Previous Failure**: {{ retry_context.failure_reason }}
      **What to improve**: {{ retry_context.improvements | join(', ') }}
      {% if retry_context.previous_errors %}
      **Errors from last attempt**:
      {% for error in retry_context.previous_errors %}
      - {{ error }}
      {% endfor %}
      {% endif %}
      {% endif %}

      ## Project Context
      Working Directory: {{ working_directory }}
      {% if project_goals %}
      Project Goals:
      {{ project_goals | truncate(500) }}
      {% endif %}

      {% if git_context %}
      ## Recent Changes (Git)
      {% if git_context.recent_commits %}
      Recent commits in this branch:
      {% for commit in git_context.recent_commits[:3] %}
      - {{ commit.hash[:7] }}: {{ commit.message }} ({{ commit.author }}, {{ commit.timestamp }})
      {% endfor %}
      {% endif %}
      {% if git_context.current_branch %}
      Current branch: {{ git_context.current_branch }}
      {% endif %}
      {% if git_context.uncommitted_changes %}
      ⚠️  {{ git_context.uncommitted_changes }} uncommitted changes
      {% endif %}
      {% endif %}

      {% if current_files %}
      ## Current Active Files
      {% for file in current_files %}
      - {{ file.path }} ({{ file.size }} bytes, last modified: {{ file.modified }})
      {% endfor %}
      {% endif %}

      {% if recent_errors %}
      ## Recent Errors to Address
      {% for error in recent_errors %}
      - {{ error.message }} ({{ error.timestamp }})
      {% endfor %}
      {% endif %}

      {% if conversation_history %}
      ## Recent Conversation
      {{ conversation_history | summarize(max_tokens=1000) }}
      {% endif %}

      {% if examples %}
      ## Example Solutions
      {% for example in examples %}
      ### Example {{ loop.index }}
      {{ example.description }}
      ```{{ example.language | default('python') }}
      {{ example.code | format_code }}
      ```
      {% endfor %}
      {% endif %}

      ## Instructions
      {{ instructions }}

      Please complete this task efficiently and report your progress.

STEP_1.2.2: Enhance validation template
  File: config/prompt_templates.yaml
  Action: REPLACE
  Location: Lines 59-94 (validation section)
  New_Template: |
    validation: |
      You are validating the work completed for the following task.

      ## Task Details
      **Task**: {{ task_title }}
      **Description**: {{ task_description }}
      **Expected Outcome**: {{ expected_outcome }}
      {% if task_dependencies %}
      **Upstream Dependencies**: {{ task_dependencies | join(', ') }}
      {% endif %}

      ## Work Submitted
      {{ work_output | truncate(3000) }}

      {% if file_changes %}
      ## Files Changed ({{ file_changes | length }} files)
      {% for change in file_changes %}
      ### {{ change.path }} ({{ change.change_type }})
      **Summary**: {{ change.summary }}
      {% if change.diff %}
      **Changes**:
      ```diff
      {{ change.diff | truncate(500) }}
      ```
      {% endif %}
      {% if change.lines_added is defined and change.lines_removed is defined %}
      **Lines**: +{{ change.lines_added }} -{{ change.lines_removed }}
      {% endif %}
      {% endfor %}
      {% endif %}

      {% if git_validation %}
      ## Git Validation
      **Commit Hash**: {{ git_validation.commit_hash }}
      **Files in Commit**: {{ git_validation.files_count }}
      **Commit Message**: {{ git_validation.message }}
      {% if git_validation.branch %}
      **Branch**: {{ git_validation.branch }}
      {% endif %}
      {% endif %}

      {% if dependency_impact %}
      ## Dependency Impact Analysis
      {% if dependency_impact.affected_tasks %}
      **Downstream Tasks Affected**: {{ dependency_impact.affected_tasks | join(', ') }}
      {% endif %}
      {% if dependency_impact.breaking_changes %}
      **⚠️  Potential Breaking Changes**: {{ dependency_impact.breaking_changes | length }}
      {% for breaking in dependency_impact.breaking_changes %}
      - {{ breaking }}
      {% endfor %}
      {% endif %}
      {% endif %}

      {% if test_results %}
      ## Test Results
      {{ test_results | summarize(max_tokens=500) }}
      {% endif %}

      {% if retry_context %}
      ## Retry Context
      This is attempt {{ retry_context.attempt_number }} of {{ retry_context.max_attempts }}.
      **Previous failure**: {{ retry_context.failure_reason }}
      **Improvements made**: {{ retry_context.improvements | join(', ') }}
      {% endif %}

      ## Validation Criteria
      Please assess the work against these criteria:
      {% for criterion in validation_criteria %}
      - {{ criterion }}
      {% endfor %}

      **RESPOND WITH ONLY A VALID JSON OBJECT. NO PREAMBLE OR EXPLANATION.**

      Required JSON format:
      {
        "is_valid": true,
        "quality_score": 0.85,
        "issues": ["Issue 1", "Issue 2"],
        "suggestions": ["Suggestion 1"],
        "dependency_concerns": ["Concern 1"],
        "reasoning": "Brief explanation"
      }

      Your JSON response:

STEP_1.2.3: Create context gathering helper in QualityController
  File: src/orchestration/quality_controller.py
  Action: ADD_METHOD
  Location: After __init__ method
  New_Method: |
    def _gather_m9_context(self, task_id: int, response: str) -> Dict[str, Any]:
        """Gather M9-specific context for validation.

        Args:
            task_id: Task being validated
            response: Agent response to validate

        Returns:
            Dictionary with M9 context (dependencies, git, retry)
        """
        context = {}

        # Get task info
        task = self.state_manager.get_task(task_id)
        if not task:
            return context

        # Dependency context (M9)
        if hasattr(self.state_manager, 'dependency_resolver'):
            resolver = self.state_manager.dependency_resolver

            # Get detailed dependency info
            dep_ids = resolver.get_dependencies(task_id)
            if dep_ids:
                deps_detailed = []
                for dep_id in dep_ids:
                    dep_task = self.state_manager.get_task(dep_id)
                    if dep_task:
                        deps_detailed.append({
                            'id': dep_id,
                            'title': dep_task.title,
                            'status': dep_task.status,
                            'completion_percentage': 100 if dep_task.status == 'completed' else 0
                        })
                context['task_dependencies_detailed'] = deps_detailed

            # Check dependency impact
            affected = resolver.get_dependents(task_id)
            if affected:
                context['dependency_impact'] = {
                    'affected_tasks': affected,
                    'breaking_changes': []  # Could analyze for breaking changes
                }

        # Git context (M9)
        if hasattr(self, 'git_manager') and self.git_manager:
            try:
                # Get recent commits
                commits = self.git_manager.get_recent_commits(limit=3)
                if commits:
                    context['git_context'] = {
                        'recent_commits': commits,
                        'current_branch': self.git_manager.get_current_branch()
                    }

                # Get file changes for this task
                file_changes = self.git_manager.get_changes_for_task(task_id)
                if file_changes:
                    context['file_changes'] = file_changes

            except Exception as e:
                self.logger.warning(f"Failed to gather git context: {e}")

        # Retry context (M9)
        if hasattr(self.state_manager, 'retry_manager'):
            retry_info = self.state_manager.retry_manager.get_retry_info(task_id)
            if retry_info and retry_info.get('attempt_number', 0) > 1:
                context['retry_context'] = {
                    'attempt_number': retry_info['attempt_number'],
                    'max_attempts': retry_info['max_attempts'],
                    'failure_reason': retry_info.get('last_failure', 'Unknown'),
                    'improvements': retry_info.get('improvements', []),
                    'previous_errors': retry_info.get('previous_errors', [])
                }

        return context

STEP_1.2.4: Update validate_response to use M9 context
  File: src/orchestration/quality_controller.py
  Action: MODIFY
  Location: validate_response method
  Changes:
    - Call _gather_m9_context to get context
    - Pass context to prompt generator
  Search_Pattern: "def validate_response"
  Implementation: |
    # In validate_response method, before generating validation prompt
    m9_context = self._gather_m9_context(task_id, response)

    # Merge with existing variables
    variables = {
        **base_variables,
        **m9_context
    }

    # Generate prompt with enhanced context
    prompt = self.prompt_generator.generate_prompt(
        'validation',
        variables,
        max_tokens=max_tokens
    )

STEP_1.2.5: Add GitManager integration check
  File: src/orchestration/quality_controller.py
  Action: MODIFY
  Location: __init__ method
  Changes:
    - Accept optional git_manager parameter
    - Store as instance variable
  Implementation: |
    def __init__(
        self,
        llm_interface: Any,
        prompt_generator: PromptGenerator,
        state_manager: Any,
        config: Optional[Dict[str, Any]] = None,
        git_manager: Optional[Any] = None  # ADD THIS
    ):
        # ... existing init code ...
        self.git_manager = git_manager  # ADD THIS

**Validation_Criteria**:
- [ ] task_execution template has dependency_detailed section
- [ ] task_execution template has retry_context section
- [ ] task_execution template has git_context section
- [ ] validation template has dependency_impact section
- [ ] validation template has git_validation section
- [ ] validation template has retry_context section
- [ ] validation template enforces JSON output format
- [ ] QualityController has _gather_m9_context method
- [ ] QualityController integrates M9 context in validation
- [ ] Unit test: _gather_m9_context returns expected structure
- [ ] Integration test: Validation prompt includes M9 data when available

**Test_Cases**:
```python
# test_quality_controller.py - Add these tests

def test_gather_m9_context_with_dependencies(quality_controller, mock_state_manager):
    """Test M9 context gathering includes dependency info."""
    # Setup mock task with dependencies
    task_id = 1
    mock_state_manager.dependency_resolver.get_dependencies.return_value = [2, 3]

    context = quality_controller._gather_m9_context(task_id, "test response")

    assert 'task_dependencies_detailed' in context
    assert len(context['task_dependencies_detailed']) > 0

def test_gather_m9_context_with_git(quality_controller, mock_git_manager):
    """Test M9 context gathering includes git info."""
    task_id = 1
    mock_git_manager.get_recent_commits.return_value = [
        {'hash': 'abc123', 'message': 'Test commit'}
    ]
    quality_controller.git_manager = mock_git_manager

    context = quality_controller._gather_m9_context(task_id, "test response")

    assert 'git_context' in context
    assert 'recent_commits' in context['git_context']

def test_validation_prompt_includes_m9_params(quality_controller):
    """Test that validation prompt includes M9 parameters."""
    # Setup task with dependencies and retry
    task_id = 1
    response = "Test response"

    # Mock M9 features available
    quality_controller.state_manager.dependency_resolver = Mock()
    quality_controller.state_manager.retry_manager = Mock()
    quality_controller.git_manager = Mock()

    result = quality_controller.validate_response(response, task_id, {})

    # Check that prompt was generated with M9 context
    # (Would need to capture prompt generation call)
    assert result is not None
```

**Success_Metrics**:
- Metric: Validation prompts include dependency info when available
- Metric: Validation prompts include git context when available
- Metric: Validation prompts include retry context on retries
- Target: 100% of validations with M9 data include it in prompt

---

### TASK_1.3: Structured JSON Output Enforcement

**ID**: TASK_1.3
**Priority**: MEDIUM
**Estimated_Duration**: 3-4 hours
**Dependencies**: [TASK_1.2]

**Objective**: Reduce JSON parsing failures by enforcing structured output and adding fallback extraction.

**Files_Modified**:
- config/prompt_templates.yaml (completed in TASK_1.2)
- src/orchestration/quality_controller.py
- src/orchestration/decision_engine.py

**Implementation_Steps**:

STEP_1.3.1: Add JSON extraction utility
  File: src/utils/json_extractor.py
  Action: CREATE
  Content: |
    """JSON extraction utilities for LLM responses."""

    import json
    import logging
    import re
    from typing import Optional, Dict, Any

    logger = logging.getLogger(__name__)


    def extract_json(response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response that may have extra text.

        Tries multiple strategies:
        1. Parse response directly
        2. Find JSON block with regex
        3. Find content between first { and last }
        4. Extract from markdown code block

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict or None if extraction fails

        Example:
            >>> extract_json('Sure! {"key": "value"}')
            {'key': 'value'}
            >>> extract_json('```json\\n{"key": "value"}\\n```')
            {'key': 'value'}
        """
        if not response:
            return None

        response = response.strip()

        # Strategy 1: Direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Find JSON with regex (greedy, captures outermost braces)
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            # Try each match (usually just one)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        # Strategy 3: Find content between first { and last }
        try:
            first_brace = response.index('{')
            last_brace = response.rindex('}')
            json_str = response[first_brace:last_brace + 1]
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            pass

        # Strategy 4: Extract from markdown code block
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(code_block_pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to extract JSON from response: {response[:200]}...")
        return None


    def validate_json_structure(
        data: Dict[str, Any],
        required_keys: list,
        optional_keys: Optional[list] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate JSON structure has required keys.

        Args:
            data: Parsed JSON data
            required_keys: List of required key names
            optional_keys: List of optional key names

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> validate_json_structure({'a': 1}, ['a', 'b'])
            (False, "Missing required keys: ['b']")
            >>> validate_json_structure({'a': 1, 'b': 2}, ['a', 'b'])
            (True, None)
        """
        if not isinstance(data, dict):
            return False, "Response is not a JSON object"

        missing = [key for key in required_keys if key not in data]
        if missing:
            return False, f"Missing required keys: {missing}"

        return True, None

STEP_1.3.2: Update QualityController to use JSON extraction
  File: src/orchestration/quality_controller.py
  Action: MODIFY
  Location: validate_response method
  Changes:
    - Import extract_json and validate_json_structure
    - Use extract_json to parse LLM response
    - Validate structure before returning
  Implementation: |
    from src.utils.json_extractor import extract_json, validate_json_structure

    # In validate_response method, after getting LLM response
    raw_response = self.llm_interface.send_prompt(validation_prompt)

    # Extract JSON from response
    validation_result = extract_json(raw_response)

    if validation_result is None:
        self.logger.error(f"Failed to parse validation response: {raw_response[:500]}")
        # Return default failed validation
        return {
            'is_valid': False,
            'quality_score': 0.0,
            'issues': [f'Failed to parse LLM response: {raw_response[:200]}'],
            'suggestions': ['LLM did not return valid JSON'],
            'reasoning': 'Parse failure'
        }

    # Validate structure
    is_valid, error = validate_json_structure(
        validation_result,
        required_keys=['is_valid', 'quality_score', 'issues', 'suggestions'],
        optional_keys=['dependency_concerns', 'reasoning']
    )

    if not is_valid:
        self.logger.error(f"Validation response missing required keys: {error}")
        # Add missing keys with defaults
        validation_result.setdefault('is_valid', False)
        validation_result.setdefault('quality_score', 0.0)
        validation_result.setdefault('issues', [error])
        validation_result.setdefault('suggestions', [])

    return validation_result

STEP_1.3.3: Update DecisionEngine similarly
  File: src/orchestration/decision_engine.py
  Action: MODIFY
  Location: decide_next_action method
  Changes:
    - Use extract_json for parsing decision responses
    - Handle parse failures gracefully
  Search_Pattern: "json.loads|parse.*response"

STEP_1.3.4: Add tests for JSON extraction
  File: tests/test_json_extractor.py
  Action: CREATE
  Content: |
    """Tests for JSON extraction utilities."""

    import pytest
    from src.utils.json_extractor import extract_json, validate_json_structure


    class TestExtractJson:
        """Test JSON extraction from LLM responses."""

        def test_extract_plain_json(self):
            """Test extraction of plain JSON."""
            response = '{"key": "value", "number": 42}'
            result = extract_json(response)
            assert result == {"key": "value", "number": 42}

        def test_extract_json_with_preamble(self):
            """Test extraction when LLM adds preamble."""
            response = 'Sure, here is the JSON:\n{"key": "value"}'
            result = extract_json(response)
            assert result == {"key": "value"}

        def test_extract_json_with_postamble(self):
            """Test extraction when LLM adds explanation after."""
            response = '{"key": "value"}\nI hope this helps!'
            result = extract_json(response)
            assert result == {"key": "value"}

        def test_extract_json_from_markdown(self):
            """Test extraction from markdown code block."""
            response = '```json\n{"key": "value"}\n```'
            result = extract_json(response)
            assert result == {"key": "value"}

        def test_extract_nested_json(self):
            """Test extraction of nested JSON."""
            response = '{"outer": {"inner": "value"}}'
            result = extract_json(response)
            assert result == {"outer": {"inner": "value"}}

        def test_extract_json_with_arrays(self):
            """Test extraction with array values."""
            response = '{"items": ["a", "b", "c"]}'
            result = extract_json(response)
            assert result == {"items": ["a", "b", "c"]}

        def test_extract_returns_none_on_invalid(self):
            """Test that extraction returns None for invalid JSON."""
            response = 'This is not JSON at all'
            result = extract_json(response)
            assert result is None

        def test_extract_handles_empty_string(self):
            """Test handling of empty response."""
            result = extract_json('')
            assert result is None


    class TestValidateJsonStructure:
        """Test JSON structure validation."""

        def test_validate_all_required_present(self):
            """Test validation passes when all required keys present."""
            data = {"a": 1, "b": 2, "c": 3}
            is_valid, error = validate_json_structure(data, ["a", "b"])
            assert is_valid is True
            assert error is None

        def test_validate_missing_required(self):
            """Test validation fails when required keys missing."""
            data = {"a": 1}
            is_valid, error = validate_json_structure(data, ["a", "b", "c"])
            assert is_valid is False
            assert "b" in error and "c" in error

        def test_validate_not_dict(self):
            """Test validation fails for non-dict data."""
            is_valid, error = validate_json_structure([], ["key"])
            assert is_valid is False
            assert "not a JSON object" in error

**Validation_Criteria**:
- [ ] JSON extraction utility created
- [ ] extract_json handles plain JSON
- [ ] extract_json handles JSON with preamble
- [ ] extract_json handles markdown code blocks
- [ ] extract_json returns None for invalid input
- [ ] validate_json_structure checks required keys
- [ ] QualityController uses extract_json
- [ ] DecisionEngine uses extract_json
- [ ] Tests cover all extraction strategies
- [ ] Parse failures handled gracefully (no crashes)

**Success_Metrics**:
- Metric: Reduction in JSON parse failures
- Baseline: Current parse failure rate (unknown, needs measurement)
- Target: <5% parse failure rate after implementation
- Metric: All validation responses parseable
- Target: 95%+ success rate

---

## PHASE_2: MEASUREMENT_AND_TRACKING

### TASK_2.1: Parameter Effectiveness Tracking

**ID**: TASK_2.1
**Priority**: HIGH
**Estimated_Duration**: 6-8 hours
**Dependencies**: [TASK_1.1, TASK_1.2]

**Objective**: Add infrastructure to track which parameters help Qwen make accurate decisions.

**Implementation_Steps**:

STEP_2.1.1: Create ParameterEffectiveness model
  File: src/core/models.py
  Action: ADD_CLASS
  Location: After PatternLearning class
  New_Class: |
    class ParameterEffectiveness(Base):
        """Track which parameters help LLM make accurate decisions.

        Records which parameters were included in prompts and whether
        the resulting LLM decision was accurate (as determined by
        later human review or test outcomes).

        Attributes:
            id: Primary key
            template_name: Which template was used
            parameter_name: Which parameter (e.g., 'file_changes', 'retry_context')
            was_included: Whether parameter fit in token budget
            validation_accurate: Whether LLM validation matched reality (nullable)
            task_id: Associated task
            prompt_token_count: Total tokens in prompt
            parameter_token_count: Tokens used by this parameter
            timestamp: When this was recorded
        """
        __tablename__ = 'parameter_effectiveness'

        id = Column(Integer, primary_key=True)
        template_name = Column(String(100), nullable=False, index=True)
        parameter_name = Column(String(100), nullable=False, index=True)
        was_included = Column(Boolean, nullable=False, index=True)
        validation_accurate = Column(Boolean, nullable=True, index=True)

        # Context
        task_id = Column(Integer, ForeignKey('task_state.id'), nullable=True, index=True)
        prompt_token_count = Column(Integer, nullable=True)
        parameter_token_count = Column(Integer, nullable=True)

        # Metadata
        timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)

        # Relationships
        task = relationship('TaskState', backref='parameter_usage')

        def __repr__(self):
            return (
                f"<ParameterEffectiveness("
                f"template={self.template_name}, "
                f"param={self.parameter_name}, "
                f"included={self.was_included}, "
                f"accurate={self.validation_accurate})>"
            )

STEP_2.1.2: Add database migration
  File: migrations/add_parameter_effectiveness.py
  Action: CREATE
  Content: |
    """Add parameter_effectiveness table.

    Revision ID: 010
    Create Date: 2025-11-03
    """
    from alembic import op
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID


    def upgrade():
        """Create parameter_effectiveness table."""
        op.create_table(
            'parameter_effectiveness',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('template_name', sa.String(100), nullable=False),
            sa.Column('parameter_name', sa.String(100), nullable=False),
            sa.Column('was_included', sa.Boolean(), nullable=False),
            sa.Column('validation_accurate', sa.Boolean(), nullable=True),
            sa.Column('task_id', sa.Integer(), nullable=True),
            sa.Column('prompt_token_count', sa.Integer(), nullable=True),
            sa.Column('parameter_token_count', sa.Integer(), nullable=True),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['task_id'], ['task_state.id'])
        )

        # Create indexes
        op.create_index('ix_param_eff_template', 'parameter_effectiveness', ['template_name'])
        op.create_index('ix_param_eff_parameter', 'parameter_effectiveness', ['parameter_name'])
        op.create_index('ix_param_eff_included', 'parameter_effectiveness', ['was_included'])
        op.create_index('ix_param_eff_accurate', 'parameter_effectiveness', ['validation_accurate'])
        op.create_index('ix_param_eff_task', 'parameter_effectiveness', ['task_id'])
        op.create_index('ix_param_eff_timestamp', 'parameter_effectiveness', ['timestamp'])


    def downgrade():
        """Drop parameter_effectiveness table."""
        op.drop_table('parameter_effectiveness')

STEP_2.1.3: Add tracking methods to StateManager
  File: src/core/state.py
  Action: ADD_METHODS
  Location: After existing tracking methods
  New_Methods: |
    def log_parameter_usage(
        self,
        template_name: str,
        parameter_name: str,
        was_included: bool,
        token_count: int,
        task_id: Optional[int] = None,
        prompt_token_count: Optional[int] = None
    ) -> None:
        """Log parameter usage for effectiveness tracking.

        Args:
            template_name: Template used (e.g., 'validation')
            parameter_name: Parameter name (e.g., 'file_changes')
            was_included: Whether parameter fit in token budget
            token_count: Tokens used by this parameter
            task_id: Associated task ID
            prompt_token_count: Total prompt tokens
        """
        with self._lock:
            session = self._get_session()
            try:
                record = ParameterEffectiveness(
                    template_name=template_name,
                    parameter_name=parameter_name,
                    was_included=was_included,
                    task_id=task_id,
                    parameter_token_count=token_count,
                    prompt_token_count=prompt_token_count,
                    validation_accurate=None  # Set later via update
                )
                session.add(record)
                session.commit()
                self.logger.debug(
                    f"Logged parameter usage: {template_name}.{parameter_name} "
                    f"(included={was_included}, tokens={token_count})"
                )
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to log parameter usage: {e}")
                raise

    def update_validation_accuracy(
        self,
        task_id: int,
        was_accurate: bool,
        window_minutes: int = 60
    ) -> int:
        """Update validation accuracy for recent parameter usage.

        When we learn whether a validation was accurate (from human review
        or test results), update all parameter usage records for that task
        within the time window.

        Args:
            task_id: Task ID
            was_accurate: Whether validation was accurate
            window_minutes: Time window to update (default 60 min)

        Returns:
            Number of records updated
        """
        with self._lock:
            session = self._get_session()
            try:
                cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)

                updated = session.query(ParameterEffectiveness).filter(
                    ParameterEffectiveness.task_id == task_id,
                    ParameterEffectiveness.timestamp >= cutoff,
                    ParameterEffectiveness.validation_accurate.is_(None)
                ).update(
                    {'validation_accurate': was_accurate},
                    synchronize_session=False
                )

                session.commit()
                self.logger.info(
                    f"Updated {updated} parameter usage records for task {task_id} "
                    f"(accurate={was_accurate})"
                )
                return updated
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to update validation accuracy: {e}")
                raise

    def get_parameter_effectiveness(
        self,
        template_name: str,
        min_samples: int = 20
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze which parameters correlate with accurate validation.

        Args:
            template_name: Template to analyze (e.g., 'validation')
            min_samples: Minimum samples required per parameter

        Returns:
            Dict mapping parameter names to effectiveness metrics:
            {
                'param_name': {
                    'accuracy_when_included': 0.85,
                    'accuracy_when_excluded': 0.70,
                    'sample_count': 50,
                    'impact_score': 0.15  # Difference in accuracy
                }
            }
        """
        with self._lock:
            session = self._get_session()
            try:
                # Get accuracy when parameter is included
                included = session.query(
                    ParameterEffectiveness.parameter_name,
                    func.avg(
                        case((ParameterEffectiveness.validation_accurate == True, 1.0), else_=0.0)
                    ).label('accuracy'),
                    func.count(ParameterEffectiveness.id).label('count')
                ).filter(
                    ParameterEffectiveness.template_name == template_name,
                    ParameterEffectiveness.was_included == True,
                    ParameterEffectiveness.validation_accurate.isnot(None)
                ).group_by(
                    ParameterEffectiveness.parameter_name
                ).having(
                    func.count(ParameterEffectiveness.id) >= min_samples
                ).all()

                # Get accuracy when parameter is excluded
                excluded = session.query(
                    ParameterEffectiveness.parameter_name,
                    func.avg(
                        case((ParameterEffectiveness.validation_accurate == True, 1.0), else_=0.0)
                    ).label('accuracy')
                ).filter(
                    ParameterEffectiveness.template_name == template_name,
                    ParameterEffectiveness.was_included == False,
                    ParameterEffectiveness.validation_accurate.isnot(None)
                ).group_by(
                    ParameterEffectiveness.parameter_name
                ).all()

                excluded_dict = {param: acc for param, acc in excluded}

                # Build result
                result = {}
                for param, accuracy_included, count in included:
                    accuracy_excluded = excluded_dict.get(param, 0.0)
                    result[param] = {
                        'accuracy_when_included': float(accuracy_included),
                        'accuracy_when_excluded': float(accuracy_excluded),
                        'sample_count': count,
                        'impact_score': float(accuracy_included - accuracy_excluded)
                    }

                return result
            except Exception as e:
                self.logger.error(f"Failed to get parameter effectiveness: {e}")
                raise

STEP_2.1.4: Integrate tracking in PromptGenerator
  File: src/llm/prompt_generator.py
  Action: MODIFY
  Location: generate_prompt method
  Changes:
    - Track which parameters were included
    - Return metadata about parameter usage
    - Add optional return_metadata parameter
  Implementation: |
    def generate_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any],
        max_tokens: Optional[int] = None,
        enable_optimization: bool = True,
        enable_caching: bool = True,
        return_metadata: bool = False,  # ADD THIS
        **kwargs
    ) -> Union[str, Dict[str, Any]]:  # Can return dict if return_metadata=True
        """Generate a prompt from template with variables.

        Args:
            template_name: Name of template to use
            variables: Variables to substitute in template
            max_tokens: Optional maximum token budget
            enable_optimization: Whether to optimize for token count
            enable_caching: Whether to use cached result if available
            return_metadata: If True, return dict with prompt and metadata
            **kwargs: Additional options (passed to template rendering)

        Returns:
            Generated prompt string, or dict with 'prompt' and 'metadata' if return_metadata=True
        """
        # ... existing generation code ...

        if return_metadata:
            # Track which variables were actually used in the rendered prompt
            # (by checking if they appear in the final prompt)
            parameters_used = {}
            for var_name, var_value in all_vars.items():
                if var_value and str(var_value) in prompt:
                    # Estimate tokens for this parameter
                    param_tokens = self.llm_interface.estimate_tokens(str(var_value))
                    parameters_used[var_name] = {
                        'included': True,
                        'tokens': param_tokens
                    }
                else:
                    parameters_used[var_name] = {
                        'included': False,
                        'tokens': 0
                    }

            return {
                'prompt': prompt,
                'metadata': {
                    'template_name': template_name,
                    'total_tokens': self.llm_interface.estimate_tokens(prompt),
                    'parameters_used': parameters_used,
                    'optimized': enable_optimization and max_tokens is not None
                }
            }

        return prompt

STEP_2.1.5: Update QualityController to log parameter usage
  File: src/orchestration/quality_controller.py
  Action: MODIFY
  Location: validate_response method
  Changes:
    - Request metadata from prompt generation
    - Log parameter usage to StateManager
  Implementation: |
    # Generate validation prompt with metadata
    prompt_info = self.prompt_generator.generate_prompt(
        'validation',
        variables,
        max_tokens=max_tokens,
        return_metadata=True  # Request metadata
    )

    prompt = prompt_info['prompt']
    metadata = prompt_info['metadata']

    # Perform validation
    raw_response = self.llm_interface.send_prompt(prompt)
    validation_result = extract_json(raw_response)

    # Log parameter usage for later effectiveness analysis
    for param_name, param_data in metadata['parameters_used'].items():
        self.state_manager.log_parameter_usage(
            template_name='validation',
            parameter_name=param_name,
            was_included=param_data['included'],
            token_count=param_data['tokens'],
            task_id=task_id,
            prompt_token_count=metadata['total_tokens']
        )

    # validation_accurate will be set later via update_validation_accuracy
    # when we know if this validation was correct

    return validation_result

**Validation_Criteria**:
- [ ] ParameterEffectiveness model created
- [ ] Database migration created
- [ ] StateManager has log_parameter_usage method
- [ ] StateManager has update_validation_accuracy method
- [ ] StateManager has get_parameter_effectiveness method
- [ ] PromptGenerator supports return_metadata
- [ ] QualityController logs parameter usage
- [ ] Unit test: log_parameter_usage stores record
- [ ] Unit test: get_parameter_effectiveness returns metrics
- [ ] Integration test: Full flow from validation to effectiveness analysis

**Test_Cases**:
```python
# test_parameter_tracking.py

def test_log_parameter_usage(state_manager):
    """Test logging parameter usage."""
    state_manager.log_parameter_usage(
        template_name='validation',
        parameter_name='file_changes',
        was_included=True,
        token_count=150,
        task_id=1,
        prompt_token_count=2000
    )

    # Verify record created
    session = state_manager._get_session()
    record = session.query(ParameterEffectiveness).filter_by(
        parameter_name='file_changes'
    ).first()

    assert record is not None
    assert record.was_included is True
    assert record.token_count == 150

def test_update_validation_accuracy(state_manager):
    """Test updating validation accuracy."""
    # Create usage records
    task_id = 1
    state_manager.log_parameter_usage('validation', 'param1', True, 100, task_id)
    state_manager.log_parameter_usage('validation', 'param2', True, 50, task_id)

    # Update accuracy
    updated = state_manager.update_validation_accuracy(task_id, was_accurate=True)

    assert updated == 2

    # Verify records updated
    session = state_manager._get_session()
    records = session.query(ParameterEffectiveness).filter_by(task_id=task_id).all()
    assert all(r.validation_accurate is True for r in records)

def test_get_parameter_effectiveness(state_manager):
    """Test parameter effectiveness analysis."""
    # Create sample data
    for i in range(30):
        # file_changes included -> 85% accurate
        state_manager.log_parameter_usage('validation', 'file_changes', True, 150, i)
        state_manager.update_validation_accuracy(i, was_accurate=(i % 100 < 85))

        # file_changes excluded -> 70% accurate
        state_manager.log_parameter_usage('validation', 'file_changes', False, 0, i+100)
        state_manager.update_validation_accuracy(i+100, was_accurate=(i % 100 < 70))

    # Analyze effectiveness
    results = state_manager.get_parameter_effectiveness('validation', min_samples=20)

    assert 'file_changes' in results
    assert results['file_changes']['accuracy_when_included'] > 0.80
    assert results['file_changes']['impact_score'] > 0.10  # Positive impact
```

**Success_Metrics**:
- Metric: Parameter usage logged for all validations
- Target: 100% of validations logged
- Metric: Effectiveness analysis available after 20+ samples
- Target: Analysis returns data for all tracked parameters
- Metric: High-impact parameters identified
- Target: Identify top 3 parameters by impact_score

---

## PHASE_3: ADVANCED_OPTIMIZATION

### TASK_3.1: Template-Specific Weight Tuning

**ID**: TASK_3.1
**Priority**: MEDIUM
**Estimated_Duration**: 4-5 hours
**Dependencies**: [TASK_1.1, TASK_2.1]

**Objective**: Tune context priority weights based on template type for optimal context selection.

**Implementation_Steps**:

STEP_3.1.1: Add template-specific weights to ContextManager
  File: src/utils/context_manager.py
  Action: ADD_CONSTANT
  Location: After PRIORITY_BY_TEMPLATE
  New_Constant: |
    # Template-specific scoring weights
    WEIGHTS_BY_TEMPLATE = {
        'task_execution': {
            'recency': 0.2,
            'relevance': 0.5,  # High - need relevant code examples
            'importance': 0.2,
            'size_efficiency': 0.1
        },
        'validation': {
            'recency': 0.1,
            'relevance': 0.2,
            'importance': 0.6,  # High - need critical validation facts
            'size_efficiency': 0.1
        },
        'error_analysis': {
            'recency': 0.5,  # High - recent errors most relevant
            'relevance': 0.3,
            'importance': 0.2,
            'size_efficiency': 0.0
        },
        'decision': {
            'recency': 0.3,
            'relevance': 0.2,
            'importance': 0.4,
            'size_efficiency': 0.1
        },
        'default': {
            'recency': 0.3,
            'relevance': 0.4,
            'importance': 0.2,
            'size_efficiency': 0.1
        }
    }

STEP_3.1.2: Update _score_context_item to use template weights
  File: src/utils/context_manager.py
  Action: MODIFY
  Location: _score_context_item method (lines 191-259)
  Changes:
    - Accept template_name parameter
    - Use WEIGHTS_BY_TEMPLATE[template_name] instead of class constants
  Implementation: |
    def _score_context_item(
        self,
        item: Dict[str, Any],
        task: Optional[Task],
        priority_order: List[str],
        template_name: Optional[str] = None  # ADD THIS
    ) -> float:
        """Score a single context item.

        Args:
            item: Context item
            task: Optional task
            priority_order: Type priority ordering
            template_name: Template type for weight selection

        Returns:
            Score (0.0-1.0)
        """
        # Get template-specific weights
        if template_name and template_name in self.WEIGHTS_BY_TEMPLATE:
            weights = self.WEIGHTS_BY_TEMPLATE[template_name]
        else:
            weights = self.WEIGHTS_BY_TEMPLATE['default']

        score = 0.0

        # Recency score
        # ... existing recency calculation ...
        score += recency_score * weights['recency']  # Use template weight

        # Relevance score
        # ... existing relevance calculation ...
        score += relevance_score * weights['relevance']  # Use template weight

        # Importance score
        # ... existing importance calculation ...
        score += importance_score * weights['importance']  # Use template weight

        # Size efficiency score
        # ... existing efficiency calculation ...
        score += efficiency_score * weights['size_efficiency']  # Use template weight

        return min(1.0, max(0.0, score))

STEP_3.1.3: Update prioritize_context to pass template_name
  File: src/utils/context_manager.py
  Action: MODIFY
  Location: prioritize_context method (lines 152-189)
  Changes:
    - Add template_name parameter
    - Pass to _score_context_item
  Implementation: |
    def prioritize_context(
        self,
        items: List[Dict[str, Any]],
        task: Optional[Task] = None,
        priority_order: Optional[List[str]] = None,
        template_name: Optional[str] = None  # ADD THIS
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Prioritize context items by relevance score."""
        priority_order = priority_order or self.DEFAULT_PRIORITY_ORDER
        scored_items = []

        for item in items:
            score = self._score_context_item(
                item, task, priority_order, template_name  # PASS template_name
            )
            scored_items.append((item, score))

        scored_items.sort(key=lambda x: x[1], reverse=True)
        return scored_items

STEP_3.1.4: Update build_context to use template_name throughout
  File: src/utils/context_manager.py
  Action: MODIFY
  Location: build_context method (lines 89-150)
  Changes:
    - Pass template_name to prioritize_context
  Implementation: |
    # In build_context, around line 118
    prioritized = self.prioritize_context(
        items, None, priority_order, template_name  # PASS template_name
    )

**Validation_Criteria**:
- [ ] WEIGHTS_BY_TEMPLATE dict added
- [ ] _score_context_item uses template-specific weights
- [ ] prioritize_context accepts and passes template_name
- [ ] build_context passes template_name through chain
- [ ] Unit test: Validation template uses importance-heavy weights
- [ ] Unit test: Task execution template uses relevance-heavy weights
- [ ] Unit test: Different templates produce different scores for same items

**Test_Cases**:
```python
# test_context_manager.py

def test_template_specific_weights(context_manager):
    """Test that different templates use different scoring weights."""
    # Create items where one is recent, one is important
    items = [
        {
            'type': 'recent_item',
            'content': 'Recent content',
            'priority': 5,
            'timestamp': datetime.now(UTC)
        },
        {
            'type': 'important_item',
            'content': 'Important content',
            'priority': 10,
            'timestamp': datetime.now(UTC) - timedelta(days=30)
        }
    ]

    # Error analysis template (recency=0.5) should prefer recent
    error_scores = context_manager.prioritize_context(
        items, template_name='error_analysis'
    )
    assert error_scores[0][0]['type'] == 'recent_item'

    # Validation template (importance=0.6) should prefer important
    validation_scores = context_manager.prioritize_context(
        items, template_name='validation'
    )
    assert validation_scores[0][0]['type'] == 'important_item'
```

**Success_Metrics**:
- Metric: Context ordering differs by template type
- Target: At least 30% difference in scores for same items across templates
- Metric: Validation uses importance-heavy weights
- Target: Importance weight >= 0.6 for validation template

---

## EXECUTION_ORDER

1. TASK_1.1 (Template-Specific Priorities) - 4-6 hours
2. TASK_1.2 (Enhanced M9 Parameters) - 6-8 hours
3. TASK_1.3 (JSON Extraction) - 3-4 hours
4. TASK_2.1 (Parameter Tracking) - 6-8 hours
5. TASK_3.1 (Weight Tuning) - 4-5 hours

**Total Estimated Time**: 23-31 hours (3-4 working days)

---

## VALIDATION_CHECKLIST

After completing all tasks:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Test coverage >= 85% for new code
- [ ] No regressions in existing functionality
- [ ] Documentation updated
- [ ] PARAMETER_REVIEW_ANALYSIS.md marked as implemented
- [ ] Performance benchmarks show improvement
- [ ] Manual validation with real orchestration tasks

---

## SUCCESS_CRITERIA

**Phase 1 Complete**:
- Template-specific context priorities implemented
- M9 parameters fully integrated in templates
- JSON parsing failure rate < 5%
- All Phase 1 tests passing

**Phase 2 Complete**:
- Parameter effectiveness tracking operational
- At least 50 validation samples logged
- Effectiveness analysis returns meaningful data

**Phase 3 Complete**:
- Template-specific weights tuned
- Context selection differs appropriately by template
- A/B tests show improvement over baseline

**Overall Success**:
- 15-25% improvement in validation accuracy (measured via manual review)
- 20% reduction in token waste (fewer truncations)
- 30-50% reduction in JSON parse failures
- System ready for production use with M9 features
