# Decision Hybrid Prompt Template

This template shows the structure of a hybrid prompt for orchestration decisions.

## Format

```
<METADATA>
{
  "prompt_type": "decision",
  "task_id": <task_id>,
  "decision_context": {
    "decision_type": "next_action|escalate|retry|decompose|approve",
    "current_state": "in_progress|completed|failed|blocked",
    "agent_response": {
      "status": "<status>",
      "files_modified": ["<files>"],
      "confidence": <0.0-1.0>
    },
    "validation_results": {
      "is_valid": <true|false>,
      "quality_score": <0-100>,
      "violations": [...]
    }
  },
  "context": {
    "task_title": "<task_title>",
    "attempt_number": <number>,
    "max_retries": <number>,
    "quality_threshold": <0-100>,
    "time_elapsed_minutes": <number>
  }
}
</METADATA>

<INSTRUCTION>
You are making an orchestration decision for the Obra system.

**Decision Type**: <next_action|escalate|retry|decompose|approve>

**Current Situation**:
- Task: <task_title>
- State: <current_state>
- Attempt: #<attempt_number> of <max_retries>
- Time Elapsed: <time_elapsed> minutes

**Agent Response**:
<agent_response_summary>

**Validation Results**:
<validation_summary>

**Your Task**:
Analyze the situation and decide the next action:
- **proceed**: Accept the work and mark task complete
- **retry**: Reject and retry with improved prompt
- **escalate**: Request human review (breakpoint)
- **decompose**: Break task into smaller subtasks
- **clarify**: Ask for more information

**Output Format**:
<METADATA>
{
  "decision": "proceed|retry|escalate|decompose|clarify",
  "confidence": <0.0-1.0>,
  "reasoning": "<one_sentence_summary>",
  "next_actions": [
    {
      "action": "<action_type>",
      "target": "<what_to_act_on>",
      "priority": <1-5>
    }
  ],
  "estimated_resolution_time_minutes": <number>,
  "requires_human_input": <true|false>
}
</METADATA>

<CONTENT>
**Analysis**:
<detailed_reasoning>

**Recommendation**:
<recommended_action_with_justification>

**Risk Assessment**:
<potential_risks_of_this_decision>
</CONTENT>
</INSTRUCTION>
```

## Example

```
<METADATA>
{
  "prompt_type": "decision",
  "task_id": 123,
  "decision_context": {
    "decision_type": "next_action",
    "current_state": "completed",
    "agent_response": {
      "status": "completed",
      "files_modified": ["src/auth/handlers.py", "tests/test_auth.py"],
      "confidence": 0.85
    },
    "validation_results": {
      "is_valid": false,
      "quality_score": 65,
      "violations": [
        {
          "rule_id": "CODE_002",
          "severity": "high",
          "message": "Missing docstrings in 2 functions"
        },
        {
          "rule_id": "TEST_001",
          "severity": "medium",
          "message": "Test coverage 75% (target: 85%)"
        }
      ]
    }
  },
  "context": {
    "task_title": "Implement user authentication module",
    "attempt_number": 1,
    "max_retries": 3,
    "quality_threshold": 80,
    "time_elapsed_minutes": 25
  }
}
</METADATA>

<INSTRUCTION>
You are making an orchestration decision for the Obra system.

**Decision Type**: next_action

**Current Situation**:
- Task: Implement user authentication module
- State: completed
- Attempt: #1 of 3
- Time Elapsed: 25 minutes

**Agent Response**:
The agent completed the task and modified 2 files:
- src/auth/handlers.py
- tests/test_auth.py

Agent confidence: 85%

**Validation Results**:
Quality score: 65/100 (threshold: 80)

Violations found:
1. **HIGH severity**: Missing docstrings in 2 functions (rule CODE_002)
2. **MEDIUM severity**: Test coverage 75%, target is 85% (rule TEST_001)

**Your Task**:
Decide the next action: proceed, retry, escalate, decompose, or clarify?

**Output Format**:
<METADATA>
{
  "decision": "...",
  "confidence": 0.9,
  "reasoning": "...",
  "next_actions": [...],
  "estimated_resolution_time_minutes": 10
}
</METADATA>

<CONTENT>
...analysis and decision...
</CONTENT>
</INSTRUCTION>
```

**Expected Response**:
```
<METADATA>
{
  "decision": "retry",
  "confidence": 0.92,
  "reasoning": "Quality score 65/100 below threshold 80/100 with fixable violations, retry likely to succeed",
  "next_actions": [
    {
      "action": "retry_task",
      "target": "task_123",
      "priority": 1,
      "parameters": {
        "focus": ["add_docstrings", "increase_test_coverage"],
        "preserve_files": ["src/auth/handlers.py", "tests/test_auth.py"],
        "specific_feedback": "Add Google-style docstrings to login_user() and register_user(). Increase test coverage from 75% to 85% by adding edge case tests."
      }
    }
  ],
  "estimated_resolution_time_minutes": 10,
  "requires_human_input": false
}
</METADATA>

<CONTENT>
**Analysis**:

The task was completed successfully from a functional perspective (status: completed, confidence: 85%), but failed quality validation:

1. **Quality Score**: 65/100 vs. threshold of 80/100 (15-point gap)
2. **Violations**:
   - HIGH severity: Missing docstrings (easily fixable)
   - MEDIUM severity: Test coverage 75% vs. 85% target (10% gap)

3. **Positive Indicators**:
   - Agent confidence is high (85%)
   - No critical violations (no stubs, no syntax errors)
   - Code structure appears sound
   - This is only attempt #1 of 3

4. **Risk Factors**:
   - Time invested: 25 minutes (reasonable)
   - Violations are fixable (not architectural issues)
   - Clear path to resolution

**Recommendation**: **RETRY**

**Justification**:
1. The violations are straightforward fixes:
   - Adding docstrings takes ~5 minutes
   - Adding edge case tests takes ~5 minutes
2. We have 2 more retry attempts available
3. Agent confidence is already high (85%), fixes will increase it
4. No need for human intervention yet - issues are well-defined
5. Quality threshold of 80 is achievable with minor additions

**Specific Feedback for Retry**:
- Add Google-style docstrings to `login_user()` and `register_user()`
- Add tests for edge cases:
  - Invalid email format
  - Empty password
  - Non-existent user
  - Expired token
- This should increase coverage from 75% to 85%

**Risk Assessment**:
- **Low risk**: The fixes are additive (adding docstrings and tests), not modifying existing logic
- **High confidence**: 92% confident retry will succeed
- **Time cost**: ~10 minutes for retry vs. 30+ minutes for escalation/decomposition
- **Alternative not recommended**: Escalating to human would waste time on easily fixable issues

**Decision**: Retry with specific, actionable feedback focused on the two violations.
</CONTENT>
```

## Best Practices

1. **Include all context** - Agent response, validation results, attempt history
2. **Show thresholds** - Quality score threshold, max retries, time limits
3. **Be data-driven** - Base decisions on metrics, not intuition
4. **Provide specific feedback** - Don't just say "retry", say "retry with X changes"
5. **Assess risks** - What could go wrong with this decision?
6. **Consider alternatives** - Why this decision over the others?
7. **Estimate time** - How long will the next action take?
8. **Know when to escalate** - Some problems need human judgment
