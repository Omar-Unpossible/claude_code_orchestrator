# ADR-005: Claude-Driven Parallelization Architecture

**Status**: Accepted
**Date**: 2025-11-03
**Decision Makers**: Project Lead
**Related**: PHASE_5, PHASE_5B Implementation

---

## Context

During PHASE_5 implementation, a parallelization system was built where Obra (Qwen) would:
1. Analyze tasks and decompose them into subtasks
2. Identify parallelization opportunities using heuristics
3. Spawn multiple Claude Code agent processes
4. Merge code results from parallel agents

Upon architectural review, this approach was identified as problematic for several reasons:

### Problems with Obra-Driven Parallelization (Original PHASE_5)

**Problem 1: Qwen's Capability Limitations**
- Qwen 2.5 Coder (32B) is powerful but not at Claude Sonnet 4 level for complex reasoning
- Task decomposition requires deep codebase understanding Qwen may lack
- False positives (identifying tasks as parallel when they're not) lead to code conflicts
- Qwen operates without full codebase visibility that Claude has

**Problem 2: Obra as Code Editor (Role Violation)**
- Obra merging code from parallel agents means **Obra edits code**
- If Agent 1 modifies `auth.py` lines 10-20 and Agent 2 modifies lines 15-25, Obra must resolve conflicts
- This changes Obra from pure coordinator to working agent
- **Violates core principle**: Only Claude should touch code

**Problem 3: Context Fragmentation**
- Each parallel agent runs in isolated Claude Code session (fresh context)
- Agent 1 creates User model → Agent 2 creates Auth service → Agent 3 writes tests
- Agent 3 has no context of what Agents 1 & 2 did
- Next sequential task gets fresh session → continuity lost
- Claude's mental model of codebase diverges from reality

**Problem 4: Architectural Inconsistency**
- Original vision: Obra validates and coordinates, Claude executes
- PHASE_5 implementation: Obra decides decomposition, spawns agents, merges code
- Blur between coordinator and executor roles

---

## Decision

**We revise the parallelization architecture to be Claude-driven, not Obra-driven.**

### New Architecture: Claude-Driven Parallelization

**Obra's Role (Coordinator Only)**:
1. ✅ Analyze task complexity and estimate tokens/LOC (informational)
2. ✅ **Suggest** potential decomposition in structured prompt
3. ✅ **Ask Claude** to identify parallelization opportunities
4. ✅ Validate Claude's output for quality
5. ❌ **NEVER** decompose tasks authoritatively
6. ❌ **NEVER** spawn multiple agent processes
7. ❌ **NEVER** merge code from parallel agents

**Claude's Role (Executor)**:
1. ✅ Receive Obra's complexity analysis and suggestions
2. ✅ **Decide** whether to decompose the task
3. ✅ **Identify** parallelization opportunities in workplan
4. ✅ **Deploy agents** using Claude's Task tool (within same context)
5. ✅ **Merge code** and resolve conflicts (Claude is the expert)
6. ✅ Return final result to Obra for validation

### Separation of Concerns

| Component | Role | Analyzes Complexity | Decomposes Tasks | Spawns Agents | Touches Code | Validates Output |
|-----------|------|---------------------|------------------|---------------|--------------|------------------|
| **Obra (Qwen)** | Coordinator | ✅ Suggests | ❌ No | ❌ No | ❌ **NEVER** | ✅ Yes |
| **Claude** | Executor | ✅ Decides | ✅ Yes | ✅ Yes | ✅ **Only Claude** | ❌ No |

---

## Consequences

### Positive Consequences

✅ **Claude's Superior Reasoning**
- Claude Sonnet 4 is better at complex decomposition than Qwen 2.5 Coder
- Claude can refuse parallelization if it detects problems
- Claude has full codebase context from FileWatcher

✅ **No Code Merging by Obra**
- Obra remains pure coordinator (never edits code)
- Claude handles all merges within its context window
- Claude ensures no conflicts or overlaps

✅ **Context Continuity**
- Single Claude session sees all parallel work
- No context fragmentation across isolated processes
- Next task has full history of previous work

✅ **Proper Separation of Concerns**
- Obra: Validates, suggests, coordinates (project oversight)
- Claude: Executes, decides, touches code (implementation)

✅ **Graceful Degradation**
- If Claude chooses not to parallelize, it executes sequentially
- No forced parallelization by Obra
- Claude's judgment takes precedence

### Negative Consequences (Acceptable Trade-offs)

⚠️ **Reliance on Claude's Task Tool**
- Requires Claude Code CLI to support parallel agent deployment
- If Claude doesn't use Task tool, no parallelization
- Mitigation: This is acceptable; sequential execution is always safe

⚠️ **Less Direct Control**
- Obra cannot force parallelization
- Claude may ignore Obra's suggestions
- Mitigation: Claude's judgment is more reliable than Qwen's heuristics

⚠️ **Single Session Context Limits**
- All parallel work must fit in Claude's context window
- Very large parallel tasks may exceed limits
- Mitigation: Claude will decompose differently if context is issue

---

## Implementation Changes (PHASE_5B)

### Components to Modify

**1. TaskComplexityEstimator** (src/orchestration/complexity_estimator.py)
- **Keep**: Heuristic analysis (estimated tokens, LOC, files)
- **Keep**: Complexity scoring
- **Remove**: Authoritative decomposition into subtasks
- **Change**: Return suggestions only, not commands
- **Add**: Flag indicating "suggest_decomposition" vs "must_decompose"

**2. StructuredPromptBuilder** (src/llm/structured_prompt_builder.py)
- **Add**: Section for complexity analysis in prompt metadata
- **Add**: Section asking Claude to consider parallelization
- **Add**: Query: "Identify any independent tasks that could be developed in parallel"
- **Keep**: Rule injection system
- **Keep**: Hybrid JSON + natural language format

**3. ParallelAgentCoordinator** (src/orchestration/parallel_agent_coordinator.py)
- **Remove**: Agent spawning logic (`_spawn_agents_for_group`)
- **Remove**: Code merging logic (`_merge_agent_results`)
- **Remove**: Thread management for parallel execution
- **Keep**: RULE_SINGLE_AGENT_TESTING enforcement (moved to prompt rules)
- **Rename**: Consider renaming to `ParallelSuggestionAnalyzer` (reflects new role)

**4. Orchestrator** (src/orchestrator.py)
- **Change**: Don't call ParallelAgentCoordinator for execution
- **Change**: Pass complexity estimate to PromptGenerator as suggestion
- **Keep**: Single agent execution flow
- **Add**: Parse Claude's response for parallel work acknowledgment

**5. PromptGenerator** (src/llm/prompt_generator.py)
- **Add**: Include complexity estimate in prompt context
- **Add**: Section asking Claude about parallelization
- **Keep**: Existing template system
- **Enhance**: task_execution template with parallel identification query

### New Prompt Structure Example

```json
{
  "metadata": {
    "type": "task_execution",
    "complexity_analysis": {
      "estimated_tokens": 15000,
      "estimated_loc": 350,
      "estimated_files": 4,
      "complexity_score": 68,
      "obra_suggestion": "Consider decomposing into subtasks"
    }
  },
  "instruction": {
    "primary": "Implement the authentication module...",
    "parallelization_query": {
      "question": "Are there independent components in this task that could be developed in parallel using the Task tool?",
      "guidance": "If yes, identify the parallel tasks and deploy agents. If no, execute sequentially.",
      "safety_rules": [
        "NEVER run tests in parallel with code development",
        "Ensure parallel tasks don't modify the same files",
        "Consider dependencies before parallelizing"
      ]
    }
  }
}
```

### Response Validation

Claude's response should include:
```json
{
  "parallel_execution": {
    "used": true/false,
    "rationale": "string explaining decision",
    "tasks_parallelized": [
      {"task": "User model", "agent_id": "task_001"},
      {"task": "Auth endpoints", "agent_id": "task_002"}
    ]
  }
}
```

---

## Alternatives Considered

### Alternative 1: Keep Obra-Driven Parallelization
**Decision**: Rejected

**Rationale**:
- Violates "only Claude touches code" principle
- Context fragmentation causes continuity issues
- Qwen not capable enough for reliable decomposition
- Code merging by Obra is dangerous

### Alternative 2: Hybrid (Claude-first, Obra-fallback)
**Decision**: Rejected

**Rationale**:
- Adds complexity without clear benefit
- If Claude can't parallelize, sequential is safer than Obra forcing it
- Two parallelization paths means two failure modes
- Better to have one clear, reliable path

### Alternative 3: No Parallelization at All
**Decision**: Rejected

**Rationale**:
- Parallelization is valuable for complex tasks
- Claude's Task tool enables safe parallelization
- Loss of potential performance gains
- User explicitly wants parallel execution capability

---

## Validation Criteria (PHASE_5B Acceptance)

### Must Have
- ✅ Obra never spawns multiple agent processes
- ✅ Obra never merges code
- ✅ StructuredPromptBuilder includes parallelization query
- ✅ TaskComplexityEstimator returns suggestions, not commands
- ✅ All existing tests updated to reflect new architecture
- ✅ Integration tests validate suggestion-only mode

### Should Have
- ✅ Prompt templates include clear parallelization guidance
- ✅ Response schema includes parallel execution metadata
- ✅ Documentation updated (this ADR, README, architecture docs)
- ✅ Examples of Claude-driven parallelization in tests

### Nice to Have
- ⚠️ Metrics tracking Claude's parallelization decisions
- ⚠️ Analysis of when Claude chooses parallel vs sequential
- ⚠️ Performance comparison (with/without parallelization)

---

## Migration Path

### Phase 5B.1: Documentation & Planning (This ADR)
- Document architectural decision
- Create detailed implementation plan
- Update PHASE_5_COMPLETION_SUMMARY.md

### Phase 5B.2: Remove Obra-Level Spawning
- Remove ParallelAgentCoordinator spawning logic
- Remove code merging from Obra
- Update Orchestrator to not call coordinator for execution

### Phase 5B.3: Add Suggestion System
- Update StructuredPromptBuilder with parallelization query
- Modify TaskComplexityEstimator to return suggestions
- Update prompt templates

### Phase 5B.4: Testing & Validation
- Update all affected tests
- Add integration tests for suggestion mode
- Validate that Obra never touches code

### Phase 5B.5: Documentation Finalization
- Update README.md
- Update ARCHITECTURE.md
- Create examples

---

## References

- **Original Issue**: PHASE_5 architectural review
- **Related Decisions**:
  - ADR-004: Local Agent Architecture
  - ADR-003: File Watcher Thread Cleanup
- **Design Documents**:
  - docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md
  - docs/architecture/ARCHITECTURE.md
- **Completion Summaries**:
  - /tmp/PHASE_5_COMPLETION_SUMMARY.md (to be updated)
  - /tmp/PHASE_4_COMPLETION_SUMMARY.md

---

## Approval

**Status**: ✅ Accepted
**Date**: 2025-11-03
**Approved By**: Project Lead
**Implementation Target**: PHASE_5B (immediate)

---

**Signed**: Claude Code
**Role**: AI Assistant / Implementation Lead
**Date**: 2025-11-03
