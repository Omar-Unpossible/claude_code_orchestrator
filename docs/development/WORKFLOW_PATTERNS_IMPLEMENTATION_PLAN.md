# Workflow Patterns Implementation Plan

**Project**: Obra (Claude Code Orchestrator)
**Date**: November 15, 2025
**Based On**: WORKFLOW_PATTERNS_AUDIT_REPORT.md
**Target**: Enforce 4 critical workflow patterns in CLAUDE.md, RULES.md, and Skills
**Estimated Time**: 2-3 hours

---

## Overview

This plan implements enforcement rules for 3 missing workflow patterns (Patterns 2, 3, 4) identified in the audit. Pattern 1 (Documentation Location) is already enforced and requires no changes.

**Approach**: Follow Claude Code optimization principles implemented in commits `4617783`, `a0693b0`, `cb04a49`

---

## Success Criteria

✅ Pattern 2 (Implementation Plans): Explicit rule in CLAUDE.md requiring both natural language AND machine-optimized plans
✅ Pattern 3 (Continuation Prompts): Explicit rule with triggers for when to create prompts
✅ Pattern 4 (Git Commit Discipline): Explicit rule for commit granularity
✅ All rules use directive language (MUST/NEVER, not "should")
✅ Examples ≤10 lines (per RULE 13)
✅ Changes increase token count toward optimal ranges
✅ Validation scripts updated (optional)

---

## Phase 1: Add Rules to CLAUDE.md (45 minutes)

### Task 1.1: Add Implementation Planning Rule
**Location**: After "Rule 7: Fail-Safe Defaults" (around line 211)
**Content**: New "Rule 8: Implementation Planning Requirements"

**Rule Text** (280 tokens):
```markdown
### Rule 8: Implementation Planning Requirements

MUST create implementation plan documents BEFORE starting:
- **Epics** (3-15 sessions, large features)
- **Complex Stories** (>2 hours estimated)
- **Architectural changes** (new components/patterns)
- **Multi-phase work** (>3 distinct phases)

MUST generate BOTH:
1. **Natural Language Plan**: Context, approach, rationale, phases, examples
2. **Machine-Optimized Plan**: Directive commands, validation steps, error handling

**Locations**:
- Plans: `docs/development/<EPIC_ID>_IMPLEMENTATION_PLAN.md`
- Machine specs: `docs/development/<EPIC_ID>_MACHINE_SPEC.md`

**Templates**: See `docs/development/.templates/` for structures

**Why**: Enables shared understanding, autonomous LLM execution, seamless handoffs
```

**Token Impact**: +280 tokens to CLAUDE.md (moves toward 3K-5K target)

---

### Task 1.2: Add Continuation Prompt Rule to Context Management Section
**Location**: In "Context Management (ADR-018)" section after "Monitoring" (around line 216)
**Content**: New subsection "Continuation Prompts"

**Rule Text** (240 tokens):
```markdown
### Continuation Prompts

MUST create continuation/startup prompt WHEN:
- **Story complete** in multi-Story Epic
- **Context >60% full** (yellow/red zone)
- **Session ending** before work complete
- **Major phase complete** requiring fresh start

Prompt MUST include:
- **Context**: What's done, what's next
- **Links**: Relevant docs, ADRs, code
- **Steps**: Clear directives for continuation
- **Validation**: How to verify previous work

**Location**: `docs/development/.continuation_prompts/<WORK_ID>_<state>.md`
**Template**: `docs/development/.continuation_prompts/TEMPLATE_continuation.md`

**Why**: Seamless handoffs, context preservation, zero ramp-up time
```

**Token Impact**: +240 tokens to CLAUDE.md

---

### Task 1.3: Add Git Commit Discipline Rule
**Location**: New section after "Changelog Maintenance" (around line 388)
**Content**: "Git Commit Discipline"

**Rule Text** (220 tokens):
```markdown
## Git Commit Discipline

MUST commit AFTER:
- **Each Story** in Epic
- **Each Phase** in multi-phase work
- **Validation passing** for changes
- **Before handoff** (with continuation prompt)

**Commit Format**:
- Epic: `feat(<epic-id>): Complete Epic - <title>`
- Story: `feat(<epic-id>): Story <N> - <title>`
- Phase: `feat(<work-id>): Phase <N> - <title>`
- Fix: `fix(<context>): <description>`

NEVER commit:
- Failing tests
- Unvalidated changes
- WIP without clear marker

**Why**: Clean history, easy rollback, clear progress, code review
```

**Token Impact**: +220 tokens to CLAUDE.md

---

**Phase 1 Total**: +740 tokens to CLAUDE.md (1,649 → 2,389 tokens, closer to 3K target)

---

## Phase 2: Update RULES.md (30 minutes)

### Task 2.1: Add Quick Reference Rules
**Location**: In "✅ DO" section, after item 9 (around line 74)
**Content**: New items 10, 11, 12

**Rules** (120 tokens):
```markdown
10. **Create dual implementation plans**
    - Natural language: Context and approach
    - Machine-optimized: Executable directives
    - Location: `docs/development/`

11. **Generate continuation prompts at boundaries**
    - After each Story in Epic
    - When context >60% full
    - Before session handoff
    - Template: `.continuation_prompts/TEMPLATE_continuation.md`

12. **Commit after meaningful work units**
    - Each Story complete
    - Each Phase complete
    - Use semantic commit messages
```

**Token Impact**: +120 tokens to RULES.md

---

### Task 2.2: Update "Never" Section
**Location**: In "❌ DON'T" section, update item 9 (around line 133)
**Content**: Expand documentation rule

**Updated Rule** (60 tokens):
```markdown
9. **Never save docs to project root or /tmp**
   - Always use `docs/` subfolders
   - Plans: `docs/development/`
   - Prompts: `docs/development/.continuation_prompts/`
   - Check templates before creating
```

**Token Impact**: +20 tokens to RULES.md (net change from expansion)

---

**Phase 2 Total**: +140 tokens to RULES.md (1,727 → 1,867 tokens, closer to 2K target)

---

## Phase 3: Create project-workflow Skill (30 minutes)

### Task 3.1: Determine If Skill Needed
**Analysis**:
- Total new content: 740 + 140 = 880 tokens
- CLAUDE.md after Phase 1: 2,389 tokens (still below 3K target)
- Content is <500 tokens per section
- Used frequently (every Epic/Story)

**Decision**: DO NOT create Skill - keep in CLAUDE.md for visibility
**Reason**: Workflow patterns are core rules, should be in always-loaded context

---

## Phase 4: Create Templates (30 minutes)

### Task 4.1: Create Implementation Plan Template
**Location**: `docs/development/.templates/IMPLEMENTATION_PLAN_TEMPLATE.md`

**Content** (structured but minimal):
```markdown
# [Epic/Story ID] Implementation Plan

**Date**: YYYY-MM-DD
**Estimated Time**: X hours
**Prerequisites**: [List dependencies]

## Context

[Why this work? What problem does it solve?]

## Approach

[High-level strategy, architectural decisions]

## Phases

### Phase 1: [Name]
- [Objective]
- [Tasks]
- [Validation]

### Phase 2: [Name]
...

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Risks

| Risk | Mitigation |
|------|------------|
| [Risk] | [How to handle] |

## References

- [Link to ADR]
- [Link to related docs]
```

---

### Task 4.2: Create Machine Plan Template
**Location**: `docs/development/.templates/MACHINE_SPEC_TEMPLATE.md`

**Content**:
```markdown
# [Epic/Story ID] Machine-Optimized Implementation Spec

**Target**: Claude Code LLM (autonomous execution)
**Format**: Directive commands, validation steps

## Validation Scripts

CHECK before starting:
```bash
# Verification commands
```

## Phase 1: [Name]

STEP 1.1: [Action]
```bash
# Exact command
```

VALIDATE:
```bash
# Check command
```

IF validation FAILS → STOP, report error

...

## Error Handling

IF [condition]:
1. STOP immediately
2. REPORT: [what to show]
3. WAIT for intervention
```

---

### Task 4.3: Update Continuation Prompt Template
**Location**: Update existing `docs/development/.continuation_prompts/TEMPLATE_continuation.md`

**Changes**: Add required sections if missing
- Context summary
- Reference links
- Next steps
- Validation

---

## Phase 5: Validation & Commit (15 minutes)

### Task 5.1: Run Token Counter
```bash
./scripts/optimization/token-counter.sh
```

**Expected**:
- CLAUDE.md: 2,320 → ~2,400 tokens (still within 3K-5K target)
- RULES.md: 1,727 → ~1,870 tokens (still within 2K-4K target)

---

### Task 5.2: Validate Changes
Check:
- ✅ Directive language (MUST/NEVER)
- ✅ Examples ≤10 lines
- ✅ Proper docs/ locations
- ✅ No soft language

---

### Task 5.3: Git Commit
Following the very rule we're implementing:

```bash
git add CLAUDE.md .claude/RULES.md docs/development/

git commit -m "feat(workflow): Enforce implementation plan and continuation prompt patterns

- Add Rule 8: Implementation Planning Requirements (dual plans mandatory)
- Add Continuation Prompt requirements to Context Management
- Add Git Commit Discipline section
- Update RULES.md with workflow pattern quick reference
- Create templates for plans and prompts

Enforcement for Patterns 2, 3, 4 from audit (31.25% → 100% compliance)

Ref: docs/development/WORKFLOW_PATTERNS_AUDIT_REPORT.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Rollback Plan

If issues occur:

```bash
# Rollback commit
git revert HEAD

# Or reset to before changes
git log --oneline -5  # Find commit before workflow changes
git reset --hard <commit-sha>
```

---

## Success Validation

After implementation, verify:

1. **Audit Compliance**:
   - Pattern 1: 100% (already met)
   - Pattern 2: 100% (new rules added)
   - Pattern 3: 100% (new rules added)
   - Pattern 4: 100% (new rules added)
   - **Overall**: 100% compliance

2. **Token Counts**:
   - CLAUDE.md: Within 3K-5K range
   - RULES.md: Within 2K-4K range
   - No files exceed limits

3. **Rule Quality**:
   - All use directive language
   - All examples ≤10 lines
   - Clear, actionable guidance

4. **Documentation**:
   - Templates created
   - Existing prompts updated
   - References accurate

---

## Timeline

| Phase | Time | Description |
|-------|------|-------------|
| Phase 1 | 45 min | Add 3 rules to CLAUDE.md |
| Phase 2 | 30 min | Update RULES.md |
| Phase 3 | 0 min | Skip Skill creation (not needed) |
| Phase 4 | 30 min | Create/update templates |
| Phase 5 | 15 min | Validate and commit |
| **Total** | **2 hours** | Full implementation |

---

## Dependencies

- Recent optimization commits (`4617783`, `a0693b0`, `cb04a49`)
- Token counter script: `./scripts/optimization/token-counter.sh`
- Validation script: `./scripts/optimization/validate-structure.sh`

---

## References

- Audit Report: `docs/development/WORKFLOW_PATTERNS_AUDIT_REPORT.md`
- ADR-018: Orchestrator Session Continuity
- Continuation Prompts Guide: `docs/development/HOW_TO_USE_CONTINUATION_PROMPTS.md`
- Optimization Rules: `docs/research/claude_code_project_optimization/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md`

---

**End of Implementation Plan**

**Next**: See WORKFLOW_PATTERNS_MACHINE_SPEC.md for autonomous execution
