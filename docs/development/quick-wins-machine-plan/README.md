# Quick Wins Machine-Optimized Implementation Plan

**Purpose**: Machine-readable specifications for Claude Code to execute Quick Wins implementation
**Format**: JSON (following LLM Dev Prompt Guide v2.2 schema)
**Human-Readable Companion**: `docs/development/quick-wins-implementation-plan.md`

---

## Overview

This directory contains structured, machine-optimized specifications for implementing all 10 Quick Wins. The format is designed for Claude Code to parse and execute autonomously while maintaining full traceability and validation.

**Dual Output Format** (from guide's core principles):
- **Human-Readable**: `quick-wins-implementation-plan.md` - For developers to review and understand
- **Machine-Optimized**: This directory - For Claude Code to execute

---

## Directory Structure

```
quick-wins-machine-plan/
├── README.md                           # This file
├── plan_manifest.json                  # Master plan following guide v2.2 schema
├── tasks/                              # Individual task specifications
│   ├── T1.1.1-create-security-module.json
│   ├── T1.1.2-implement-injection-detector.json
│   ├── T1.1.3-implement-sanitizer.json
│   ├── ... (67 total tasks across 10 quick wins)
│   └── task-template.json             # Template for new tasks
├── test-specs/                         # Test specifications
│   ├── unit-test-template.json
│   ├── integration-test-template.json
│   └── performance-test-template.json
└── validation/                         # Validation scripts and checklists
    ├── validate-plan.py               # Validate plan_manifest.json against schema
    ├── validate-task.py               # Validate individual task specs
    └── acceptance-criteria-checklist.md
```

---

## How to Use This Plan

### For Claude Code (Autonomous Execution)

**Step 1: Load Plan Manifest**
```bash
# Read the master plan
cat docs/development/quick-wins-machine-plan/plan_manifest.json

# Understand structure:
# - meta: Project metadata, approval status
# - objective: Goals, user stories, success criteria
# - constraints: Technical limits, performance targets
# - dependencies: Packages, tools required
# - plan: Phases → Stories → Tasks
# - state: Current progress, validation results
```

**Step 2: Execute Tasks Sequentially**
```bash
# For each task in current story:
for task in $(jq -r '.plan.phases[0].stories[0].tasks[].task_id' plan_manifest.json); do
    # Read task spec
    TASK_SPEC="tasks/${task}-*.json"

    # Execute task following spec
    python execute_task.py "$TASK_SPEC"

    # Validate results
    python validation/validate-task.py "$TASK_SPEC"

    # Update state
    python update_state.py "$task" "completed"
done
```

**Step 3: Validation Gates**
After each story:
- Run lint: `pylint src/`
- Run type check: `mypy src/`
- Run tests: `pytest tests/`
- Verify acceptance criteria met

**Step 4: Update Plan Manifest**
```python
# Update state.completed_tasks
# Update state.current_story
# Update state.validation_results
# Save updated plan_manifest.json
```

### For Human Developers (Manual Review)

**Quick Start**:
1. Read human-readable plan first: `quick-wins-implementation-plan.md`
2. Review machine plan structure: This README
3. Inspect specific tasks: `tasks/*.json`
4. Verify against acceptance criteria: `validation/acceptance-criteria-checklist.md`

**Review Checklist**:
- [ ] Plan manifest valid (run `validation/validate-plan.py`)
- [ ] All tasks have clear specifications
- [ ] Dependencies correct (no circular deps)
- [ ] Acceptance criteria measurable
- [ ] Code scaffolding provided
- [ ] Test specs included

---

## Plan Manifest Schema

Following LLM Dev Prompt Guide v2.2 schema exactly:

```json
{
  "meta": {
    "epic_id": "QW-001",
    "created_at": "ISO-8601",
    "prompt_version": "2.2",
    "agent_version": "claude-sonnet-4-20250514",
    "approved_by": "name",
    "approved_at": "ISO-8601"
  },
  "objective": {
    "summary": "One-sentence goal",
    "user_stories": ["As a..., I want..., so that..."],
    "success_criteria": ["Observable outcome"]
  },
  "constraints": {
    "max_tokens_per_phase": 50000,
    "test_coverage_min_pct": 90,
    "performance_targets": {...},
    "security": {...}
  },
  "dependencies": {
    "existing_packages": [...],
    "new_packages": [...],
    "tools_and_resources": [...]
  },
  "plan": {
    "phases": [
      {
        "phase_id": "P1",
        "name": "Phase Name",
        "stories": [
          {
            "story_id": "S1.1",
            "description": "User story",
            "tasks": [
              {
                "task_id": "T1.1.1",
                "description": "Task description",
                "type": "code|test|doc|config",
                "dependencies": ["T1.1.0"],
                "artifacts": ["file paths"],
                "validation_rules": ["checks"]
              }
            ]
          }
        ]
      }
    ],
    "decision_records": [ADRs]
  },
  "state": {
    "current_phase": "P1",
    "current_story": "S1.1",
    "completed_tasks": [],
    "status": "planning|approved|in_progress|completed",
    "validation_results": {...}
  }
}
```

---

## Task Specification Format

Each task has a detailed JSON spec in `tasks/` directory:

```json
{
  "task_id": "T1.1.1",
  "title": "Human-readable title",
  "story_id": "S1.1",
  "epic_id": "QW-001",
  "type": "code|test|doc|config|review",
  "estimated_tokens": 1000,
  "priority": "P0-CRITICAL|P1-HIGH|P2-MEDIUM|P3-LOW",
  "dependencies": ["T1.1.0"],

  "objective": {
    "summary": "One sentence",
    "design_intent": "Why we're doing this"
  },

  "deliverables": {
    "code_artifacts": [
      {"path": "src/file.py", "purpose": "What it does", "template": "scaffold_name"}
    ],
    "documentation": [...]
  },

  "implementation_spec": {
    "step_by_step": [
      {"step": 1, "action": "Do X", "command": "...", "validation": "..."},
      ...
    ]
  },

  "code_scaffolding": {
    "src/file.py": "Complete code template with TODOs"
  },

  "acceptance_criteria": [
    {"criterion": "X works", "validation_method": "pytest", "command": "..."},
    ...
  ],

  "validation_commands": [
    {"name": "pylint", "command": "...", "expected_exit_code": 0},
    ...
  ],

  "testing_requirements": {
    "unit_tests": "Description and coverage target",
    "integration_tests": "...",
    "manual_tests": ["Step 1", "Step 2"]
  },

  "rollback_procedure": {
    "steps": ["Undo X", "Verify Y"],
    "verification": "Command to verify rollback"
  },

  "next_tasks": ["T1.1.2"],
  "references": ["Relevant docs"]
}
```

---

## Execution Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LOAD PLAN                                                │
│    Read plan_manifest.json                                  │
│    Understand epic → stories → tasks structure              │
│    Check current state (which tasks completed)              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SELECT NEXT TASK                                         │
│    Find first incomplete task in current story              │
│    Verify dependencies met (all deps in completed_tasks)    │
│    Load task specification from tasks/ directory            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. EXECUTE TASK                                             │
│    Follow implementation_spec step-by-step                  │
│    Use code_scaffolding as templates                        │
│    Create deliverables (code, tests, docs)                  │
│    Log progress and decisions                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VALIDATE TASK                                            │
│    Run validation_commands (pylint, mypy, pytest)           │
│    Check acceptance_criteria (all must pass)                │
│    Verify deliverables exist and meet specs                 │
│    Record validation results                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
                   [Pass?]
                    /   \
                   /     \
              Yes /       \ No
                 /         \
                ▼           ▼
    ┌──────────────┐   ┌────────────────┐
    │ MARK COMPLETE│   │ DEBUG & RETRY  │
    │ Update state │   │ Fix issues     │
    │ Commit       │   │ Re-validate    │
    └──────┬───────┘   └───────┬────────┘
           │                   │
           │◄──────────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ STORY COMPLETE?              │
    │ All tasks done?              │
    └──────┬─────────────────┬─────┘
           │ No              │ Yes
           ▼                 ▼
    ┌──────────────┐   ┌─────────────────┐
    │ NEXT TASK    │   │ STORY VALIDATION│
    │ Repeat loop  │   │ Run story tests │
    └──────────────┘   │ Update state    │
                       └────────┬─────────┘
                                │
                                ▼
                         ┌─────────────────┐
                         │ PHASE COMPLETE? │
                         │ All stories?    │
                         └────────┬────────┘
                                  │
                                  ▼
                           [Continue to next phase]
```

---

## Validation Framework

### Automated Validation

**Plan Validation**:
```bash
python validation/validate-plan.py plan_manifest.json
```

Checks:
- Schema compliance (matches guide v2.2)
- No circular dependencies
- All referenced tasks exist
- Acceptance criteria measurable
- Effort estimates reasonable

**Task Validation**:
```bash
python validation/validate-task.py tasks/T1.1.1-*.json
```

Checks:
- Required fields present
- Code scaffolding syntactically valid
- Validation commands runnable
- Acceptance criteria clear

**Continuous Validation** (after each task):
```bash
# Lint
pylint src/ --rcfile=.pylintrc --fail-under=9.0

# Type check
mypy src/ --config-file=mypy.ini

# Tests
pytest tests/ --cov=src --cov-report=term --cov-fail-under=90

# Security
bandit src/ -r -ll  # Low and above
```

### Manual Validation

Checklist in `validation/acceptance-criteria-checklist.md`:
- [ ] All 10 quick wins implemented
- [ ] Test coverage ≥90%
- [ ] Zero breaking changes
- [ ] Documentation complete
- [ ] Security metrics met
- [ ] Quality metrics met
- [ ] Automation metrics met

---

## Progress Tracking

### Update State After Each Task

```python
import json

# Load plan
with open('plan_manifest.json') as f:
    plan = json.load(f)

# Mark task complete
plan['state']['completed_tasks'].append('T1.1.1')

# Update current task
plan['state']['current_story'] = 'S1.1'

# Update validation results
plan['state']['validation_results'] = {
    'lint': {'status': 'passed', 'score': 9.5},
    'tests': {'status': 'passed', 'coverage': 92.3},
    'security': {'status': 'passed', 'issues': 0}
}

# Save
with open('plan_manifest.json', 'w') as f:
    json.dump(plan, f, indent=2)
```

### Generate Progress Report

```bash
python generate_report.py plan_manifest.json

# Output:
# Quick Wins Progress Report
# =========================
# Overall: 15% complete (10/67 tasks)
# Current Phase: P1 (Security Foundation)
# Current Story: S1.2 (Output Sanitization)
# Latest Validation: ✅ All checks passed
# Estimated Completion: 8 days remaining
```

---

## Error Handling

### If Task Fails Validation

1. **Review validation output**: Check which acceptance criterion failed
2. **Debug**: Run validation commands manually, inspect output
3. **Fix**: Correct the issue
4. **Re-validate**: Run validation commands again
5. **Update state**: Only mark complete after all validations pass

### If Blocked on Dependencies

1. **Check dependencies**: Verify `dependencies` field in task spec
2. **Review dependency status**: Ensure all deps in `completed_tasks`
3. **If dep failed**: Fix dependency first, then retry this task
4. **If circular dep detected**: Error - fix plan_manifest.json

### If Rollback Needed

Follow `rollback_procedure` in task spec:
1. Execute rollback steps
2. Verify rollback successful
3. Remove task from `completed_tasks`
4. Fix issue
5. Retry task

---

## Integration with Existing Obra

### Before Starting

1. **Baseline**: Run full test suite, record coverage
2. **Branch**: Create feature branch `quick-wins-implementation`
3. **Config**: Ensure Obra v1.4.0 installed and working

### During Implementation

1. **Commit per task**: `git commit -m "feat(qw-NNN): Task T1.1.1 complete"`
2. **Test continuously**: Run tests after each task
3. **Update CHANGELOG**: Add entry for each quick win

### After Completion

1. **Integration test**: Run full test suite
2. **Performance test**: Benchmark overhead
3. **Documentation review**: Ensure all docs updated
4. **Create PR**: With detailed description and metrics

---

## References

### Human-Readable Documentation
- Quick Wins Implementation Plan: `docs/development/quick-wins-implementation-plan.md`
- Best Practices Assessment: `docs/design/obra-best-practices-assessment.md`
- Roadmap: `docs/design/ROADMAP.md`

### Machine-Readable Specifications
- Plan Manifest: `plan_manifest.json` (this directory)
- Task Specs: `tasks/*.json` (this directory)
- Test Specs: `test-specs/*.json` (this directory)

### External References
- LLM Dev Prompt Guide v2.2: `docs/research/llm-dev-prompt-guide-v2_2.md`
- JSON Schema: http://json-schema.org/draft-07/schema#

---

## FAQ

**Q: Why both human-readable and machine-optimized plans?**
A: Dual output format (from guide's core principles). Humans need narrative/context, machines need structured/parseable data.

**Q: Can I execute tasks out of order?**
A: No - dependencies must be respected. Validate with `validate-plan.py` first.

**Q: What if a task spec is unclear?**
A: Refer to human-readable plan for context. If still unclear, ask for clarification before proceeding.

**Q: How do I know if validation passed?**
A: All `validation_commands` must exit with `expected_exit_code` (usually 0). All `acceptance_criteria` must be verifiable as true.

**Q: Can I modify the plan during execution?**
A: Yes, but update `plan_manifest.json` and re-validate. Document changes in decision records.

---

**Document Version**: 1.0
**Created**: 2025-11-11
**Maintained By**: Obra development team
**Claude Code Compatible**: Yes (designed for autonomous execution)
