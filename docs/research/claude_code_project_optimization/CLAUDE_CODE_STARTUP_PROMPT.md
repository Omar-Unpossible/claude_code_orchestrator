# Claude Code Startup Prompt - Obra Optimization Implementation

**PURPOSE**: Ready-to-paste prompt for fresh Claude Code session to autonomously implement all optimization fixes.

**USAGE**: Copy everything between the ===START=== and ===END=== markers and paste into Claude Code.

---

===START CLAUDE CODE PROMPT===

You are implementing Claude Code optimizations for the Obra project following a comprehensive audit and action plan.

## TASK

Autonomously implement ALL optimization fixes identified in the audit, organized into 3 phases:
- **PHASE 1 (P0)**: Critical fixes - .gitignore, soft language, Skills directory (30 min)
- **PHASE 2 (P1)**: High-impact changes - Extract 3 Skills, compress examples (4 hours)
- **PHASE 3 (P2)**: Expansion & polish - 2 more Skills, expand files, 100% compliance (3 hours)

## IMPLEMENTATION APPROACH

**MUST follow this exact sequence**:

### Step 1: Read Implementation Guide
READ: `docs/research/claude_code_project_optimization/MACHINE_IMPLEMENTATION_GUIDE.md`

This contains the COMPLETE machine-optimized execution protocol with:
- Directive commands (no prose)
- Exact validation steps
- Error handling procedures
- Line-by-line instructions

### Step 2: Read Context Documents (in order)
1. `docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_AUDIT_REPORT.md` - Detailed findings
2. `docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_ACTION_PLAN.md` - Prioritized fixes with examples
3. `docs/research/claude_code_project_optimization/IMPLEMENTATION_PLAN.md` - Human-readable plan

### Step 3: Execute Phases Sequentially

**CRITICAL RULES**:
- Execute ONE phase at a time
- VALIDATE after each task
- COMMIT after each phase
- DO NOT skip validation
- STOP on validation failure

## VALIDATION TOOLS

You have 4 scripts in `scripts/optimization/`:

```bash
# Measure token counts
./scripts/optimization/token-counter.sh

# Find soft language violations (should/consider/recommend)
./scripts/optimization/find-soft-language.sh

# Find examples >10 lines
./scripts/optimization/find-long-examples.sh

# Complete validation (all 27 rules)
./scripts/optimization/validate-structure.sh
```

**MUST run these before committing each phase.**

## PHASE EXECUTION PROTOCOL

### PHASE 1: Critical Fixes (P0)

**Tasks**:
1. Fix .gitignore (selective ignore, not blocking .claude/)
2. Change "recommended" to "MUST use" (2 instances in PROJECT.md)
3. Create .claude/skills/ directory with README.md
4. Archive OPTIMIZATION_SUMMARY.md to research folder

**Validation**:
```bash
git status | grep ".claude/PROJECT.md"  # Should appear
./scripts/optimization/find-soft-language.sh | grep -c "recommended"  # Should be 0
ls .claude/skills/README.md  # Must exist
```

**Commit** when all P0 tasks pass validation.

---

### PHASE 2: High-Impact Changes (P1)

**Tasks**:
1. Extract shell-enhancements Skill (PROJECT.md lines ~321-413 → .claude/skills/shell-enhancements/SKILL.md)
2. Extract development-tools Skill (PROJECT.md lines ~72-116 → .claude/skills/development-tools/SKILL.md)
3. Extract testing-guidelines Skill (CONSOLIDATE from CLAUDE.md:125-153, PROJECT.md:206-231, 489-508)
4. Compress 3 longest examples in CLAUDE.md (13→8, 11→8, 14→10 lines)

**Token Savings**: ~1,950 tokens from startup context

**Validation**:
```bash
ls .claude/skills/shell-enhancements/SKILL.md  # Must exist
ls .claude/skills/development-tools/SKILL.md  # Must exist
ls .claude/skills/testing-guidelines/SKILL.md  # Must exist
./scripts/optimization/token-counter.sh | grep "PROJECT.md"  # Should show decrease
./scripts/optimization/find-long-examples.sh | grep "CLAUDE.md"  # Should show 3 fewer
grep -c "Testing Patterns" .claude/PROJECT.md  # Should be 0 (deleted duplicate)
```

**Commit** when all P1 tasks pass validation.

---

### PHASE 3: Expansion & Polish (P2)

**Tasks**:
1. Create agile-workflow Skill (PROJECT.md lines ~303-319)
2. Create interactive-commands Skill (CONSOLIDATE CLAUDE.md:196-211 + PROJECT.md:284-301)
3. Compress 5 longest examples in PROJECT.md
4. Expand CLAUDE.md with 5 sections (+1,200 tokens):
   - Skills architecture
   - Context management
   - Rewind/checkpoints
   - MCP integration
   - Subagent delegation
5. Expand RULES.md with 3 sections (+864 tokens):
   - Advanced StateManager patterns
   - Common error fixes
   - Debug checklist

**Target**: 27/27 rules passing (100% compliance)

**Validation**:
```bash
./scripts/optimization/validate-structure.sh  # Must show 100% compliance
./scripts/optimization/find-long-examples.sh  # Should show 0 violations
./scripts/optimization/token-counter.sh | grep "CLAUDE.md"  # Should be 2,900-3,100
./scripts/optimization/token-counter.sh | grep "RULES.md"  # Should be 2,000-2,100
```

**Commit** when all P2 tasks pass validation.

---

## SUCCESS CRITERIA

### Final State (After All Phases)

```
CLAUDE.md:      2,900-3,100 tokens  ✅ Within target (3K-5K)
PROJECT.md:     5,500-6,500 tokens  ✅ Within target (5K-9K)
RULES.md:       2,000-2,100 tokens  ✅ Within target (2K-4K)
Skills:         7 Skills, 350 tokens metadata  ✅
Total startup:  6,500-7,500 tokens  ✅ <15K
Skills on-demand: 2,900 tokens  ✅

Compliance: 27/27 rules (100%)  ✅
Long examples: 0  ✅
Soft language: 0  ✅
.gitignore: Selective  ✅
```

### Git History
Should show 3 commits:
1. "fix: P0 critical optimizations (gitignore, soft language, Skills foundation)"
2. "feat: P1 high-impact optimizations (Skills extraction, example compression)"
3. "feat: P2 optimization complete - 100% rule compliance"

---

## CRITICAL IMPLEMENTATION NOTES

### Line Numbers Will Shift
- After editing files, line numbers change
- ALWAYS re-read files before making edits
- USE section headers/content markers to find locations
- DO NOT rely solely on line numbers from documents

### Skills Extraction Pattern
For EACH Skill:
1. Create directory: `mkdir -p .claude/skills/{skill-name}`
2. Extract content from source file
3. Create SKILL.md with:
   - Metadata header (Description, Triggers, Token Cost, Dependencies)
   - Full content from source
4. Replace source with:
   - Brief summary
   - "See Skill: {skill-name}"
   - Quick reference examples
5. Validate token reduction

### Example Compression Techniques
- Remove boilerplate code
- Use compact syntax (list comprehensions)
- Combine related lines
- Use comments instead of prose explanations
- Show key parts only, use '...' for omitted code

### Validation Discipline
- RUN validation scripts after EVERY task
- DO NOT skip to "save time"
- STOP immediately on validation failure
- Report what failed and why

### Error Handling
IF ANY validation fails:
1. STOP immediately (do not continue)
2. REPORT which validation failed
3. SHOW expected vs actual values
4. SHOW relevant script output
5. WAIT for guidance

DO NOT guess or make assumptions - follow the MACHINE_IMPLEMENTATION_GUIDE exactly.

---

## EXECUTION COMMAND

When ready, start with:

```
I will now implement the Obra Claude Code optimizations following the MACHINE_IMPLEMENTATION_GUIDE.

Starting PHASE 0: INITIALIZATION
- Reading MACHINE_IMPLEMENTATION_GUIDE.md...
```

Then proceed through each phase systematically, validating and committing as specified.

---

## EXPECTED TIMELINE

- Phase 1 (P0): 30 minutes
- Phase 2 (P1): 4 hours
- Phase 3 (P2): 3 hours
- **Total**: ~7.5 hours of autonomous implementation

Report progress at phase boundaries and stop on any validation failure for user review.

---

BEGIN IMPLEMENTATION NOW.

===END CLAUDE CODE PROMPT===

---

## Notes for User

**Before pasting**:
1. Ensure you're in a fresh Claude Code session in the project root
2. Verify all audit/plan documents exist in `docs/research/claude_code_project_optimization/`
3. Verify optimization scripts exist in `scripts/optimization/`
4. Optionally run baseline measurements first:
   ```bash
   ./scripts/optimization/token-counter.sh > baseline-tokens.txt
   ./scripts/optimization/validate-structure.sh > baseline-validation.txt
   ```

**During execution**:
- Claude Code will work autonomously through all 3 phases
- It will validate after each task
- It will commit after each phase
- It may ask for clarification if validations fail

**After completion**:
- Review the 3 commits (P0, P1, P2)
- Run final validation: `./scripts/optimization/validate-structure.sh`
- Compare before/after: `diff baseline-tokens.txt <(./scripts/optimization/token-counter.sh)`

**Rollback if needed**:
```bash
# Rollback last phase only
git revert HEAD

# Rollback all optimizations
git log --oneline -10  # Find commit before optimizations
git reset --hard <commit-sha>
```

---

## Alternative: Incremental Execution

If you prefer to supervise each phase:

**Phase 1 only**:
```
Implement PHASE 1 (P0) only from the MACHINE_IMPLEMENTATION_GUIDE.
Stop after P0 commit and report results.
```

**Then for Phase 2**:
```
Implement PHASE 2 (P1) from the MACHINE_IMPLEMENTATION_GUIDE.
Stop after P1 commit and report results.
```

**Finally for Phase 3**:
```
Implement PHASE 3 (P2) from the MACHINE_IMPLEMENTATION_GUIDE.
Stop after P2 commit and report final metrics.
```

This allows you to review and validate each phase before proceeding.
