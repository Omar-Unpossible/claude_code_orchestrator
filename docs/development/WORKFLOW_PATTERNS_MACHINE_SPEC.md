# Workflow Patterns Machine-Optimized Implementation Spec

**Target**: Claude Code LLM (autonomous execution)
**Format**: Directive commands, no prose, clear validation
**Phases**: 4 (Templates, CLAUDE.md, RULES.md, Validation)
**Duration**: ~2 hours

---

## PHASE 0: VALIDATION

### STEP 0.1: Verify Baseline
```bash
./scripts/optimization/token-counter.sh
```

VERIFY:
- CLAUDE.md: ~2,320 tokens
- RULES.md: ~1,727 tokens

IF counts differ significantly → READ audit report first

---

### STEP 0.2: Read Context
READ in order:
1. `docs/development/WORKFLOW_PATTERNS_AUDIT_REPORT.md`
2. `docs/development/WORKFLOW_PATTERNS_IMPLEMENTATION_PLAN.md`

---

## PHASE 1: CREATE TEMPLATES

**Goal**: Create template files for implementation plans and machine specs
**Time**: 30 minutes

### TASK 1.1: Create Implementation Plan Template

EXECUTE:
```bash
mkdir -p docs/development/.templates
```

WRITE: `docs/development/.templates/IMPLEMENTATION_PLAN_TEMPLATE.md`

CONTENT:
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

VALIDATE:
```bash
ls docs/development/.templates/IMPLEMENTATION_PLAN_TEMPLATE.md
```

IF missing → STOP, report error

---

### TASK 1.2: Create Machine Spec Template

WRITE: `docs/development/.templates/MACHINE_SPEC_TEMPLATE.md`

CONTENT:
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

STEP 1.2: [Next action]
...

## Phase 2: [Name]
...

## Error Handling

IF [condition]:
1. STOP immediately
2. REPORT: [what to show]
3. WAIT for intervention
```

VALIDATE:
```bash
ls docs/development/.templates/MACHINE_SPEC_TEMPLATE.md
```

---

## PHASE 2: UPDATE CLAUDE.md

**Goal**: Add 3 new rules to CLAUDE.md
**Time**: 45 minutes
**Token Addition**: +740 tokens

### TASK 2.1: Add Rule 8 - Implementation Planning

READ: `CLAUDE.md` to find insertion point
FIND: "### Rule 7: Fail-Safe Defaults" (around line 211)

INSERT AFTER Rule 7:

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

VALIDATE:
```bash
grep -c "Rule 8: Implementation Planning" CLAUDE.md  # Should be 1
```

IF grep returns 0 → STOP, report "Rule 8 not added"

---

### TASK 2.2: Add Continuation Prompts to Context Management

READ: `CLAUDE.md` to find Context Management section
FIND: "### Monitoring" under "Context Management (ADR-018)" (around line 216)

INSERT AFTER "Monitoring" subsection:

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

VALIDATE:
```bash
grep -c "Continuation Prompts" CLAUDE.md  # Should be 1
```

---

### TASK 2.3: Add Git Commit Discipline Section

FIND: "## Changelog Maintenance" section (around line 382)

INSERT AFTER "Changelog Maintenance" section:

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

VALIDATE:
```bash
grep -c "Git Commit Discipline" CLAUDE.md  # Should be 1
```

---

## PHASE 3: UPDATE RULES.md

**Goal**: Add workflow pattern quick reference
**Time**: 30 minutes
**Token Addition**: +140 tokens

### TASK 3.1: Add Items to DO Section

READ: `.claude/RULES.md`
FIND: "### ✅ DO" section, item 9 (around line 67)

INSERT AFTER item 9:

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

VALIDATE:
```bash
grep -c "Create dual implementation plans" .claude/RULES.md  # Should be 1
```

---

### TASK 3.2: Expand DON'T Item 9

FIND: Item 9 in "### ❌ DON'T" section (around line 133)

REPLACE:
```markdown
9. **Never save docs to project root or /tmp**
   - Always use `docs/` subfolders
   - Check `docs/archive/README.md` for existing content
```

WITH:
```markdown
9. **Never save docs to project root or /tmp**
   - Always use `docs/` subfolders
   - Plans: `docs/development/`
   - Prompts: `docs/development/.continuation_prompts/`
   - Check templates before creating
```

VALIDATE:
```bash
grep -c "Plans: .docs/development/" .claude/RULES.md  # Should be 1
```

---

## PHASE 4: VALIDATION & COMMIT

**Goal**: Verify changes and commit
**Time**: 15 minutes

### TASK 4.1: Run Token Counter

EXECUTE:
```bash
./scripts/optimization/token-counter.sh
```

VERIFY:
- CLAUDE.md: ~2,400-2,500 tokens (baseline 2,320 + 740 new)
- RULES.md: ~1,850-1,900 tokens (baseline 1,727 + 140 new)
- Both within target ranges (CLAUDE: 3K-5K, RULES: 2K-4K)

IF outside ranges → REVIEW changes, may need compression

---

### TASK 4.2: Validate Structure

EXECUTE:
```bash
./scripts/optimization/validate-structure.sh
```

CHECK for errors:
- ✅ No failures
- ⚠️ Warnings acceptable if files still below targets

---

### TASK 4.3: Check Directive Language

EXECUTE:
```bash
./scripts/optimization/find-soft-language.sh
```

VERIFY: 0 instances of soft language in new content

---

### TASK 4.4: Git Status Check

EXECUTE:
```bash
git status
```

EXPECTED changes:
- `CLAUDE.md`
- `.claude/RULES.md`
- `docs/development/.templates/IMPLEMENTATION_PLAN_TEMPLATE.md` (new)
- `docs/development/.templates/MACHINE_SPEC_TEMPLATE.md` (new)
- `docs/development/WORKFLOW_PATTERNS_AUDIT_REPORT.md` (existing)
- `docs/development/WORKFLOW_PATTERNS_IMPLEMENTATION_PLAN.md` (existing)
- `docs/development/WORKFLOW_PATTERNS_MACHINE_SPEC.md` (existing)

---

### TASK 4.5: Stage and Commit

EXECUTE:
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

VALIDATE commit:
```bash
git log -1 --oneline | grep "feat(workflow)"
```

IF no match → STOP, commit failed

---

## SUCCESS VALIDATION

RUN all checks:

```bash
# Token counts
./scripts/optimization/token-counter.sh > /tmp/final-tokens.txt
cat /tmp/final-tokens.txt

# Structure validation
./scripts/optimization/validate-structure.sh

# Git log
git log --oneline -5
```

VERIFY final state:
- ✅ 4 new files created (2 templates, audit, plan, machine spec)
- ✅ CLAUDE.md expanded (+740 tokens)
- ✅ RULES.md expanded (+140 tokens)
- ✅ Commit successful
- ✅ All validation passing

---

## ERROR HANDLING

IF any validation FAILS:
1. STOP immediately
2. REPORT:
   - Which validation failed
   - Expected vs actual
   - Relevant command output
3. DO NOT continue
4. WAIT for user guidance

IF token counts exceed targets:
1. REPORT overage
2. SUGGEST: Compress examples or extract to Skill
3. WAIT for approval

IF commit fails:
1. CHECK: Git status for conflicts
2. REPORT: Error message
3. WAIT for resolution

---

## ROLLBACK PROCEDURE

IF implementation needs rollback:

```bash
# Option 1: Revert commit
git revert HEAD

# Option 2: Reset to before changes
git log --oneline -5
git reset --hard <commit-sha-before-workflow-changes>
```

---

**AUTONOMOUS EXECUTION NOTES**

- Line numbers MAY shift during editing
- ALWAYS re-read files before edits
- USE section headers to find locations, not just line numbers
- VALIDATE after EVERY task
- DO NOT skip validation "to save time"
- STOP on ANY failure

---

**END OF MACHINE SPEC**

Ready for Claude Code LLM autonomous execution
