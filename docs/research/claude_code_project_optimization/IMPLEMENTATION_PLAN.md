# Obra Optimization Implementation Plan

**Project**: Obra (Claude Code Orchestrator)
**Date**: November 15, 2025
**Executor**: Claude Code (Autonomous Implementation)
**Duration**: 3-phase approach (Today → This Week → This Month)

---

## Overview

This plan implements all optimization fixes identified in the audit report. Each phase is designed for autonomous execution by Claude Code with clear validation checkpoints.

---

## PHASE 1: Critical Fixes (P0) - TODAY

**Duration**: 30 minutes
**Goal**: Fix critical violations preventing team collaboration and compliance
**Validation**: All P0 items pass in validate-structure.sh

### Task 1.1: Fix .gitignore Configuration
**File**: `.gitignore`
**Issue**: Line ~10 blocks ALL `.claude/` files (RULE 19 violation)
**Compliance**: RULE 19

**Implementation**:
```bash
# Current (find and remove)
.claude/

# Replace with (selective ignoring)
# Claude Code CLI - local files only
.claude/settings.local.json
.claude/.cache/
.claude/logs/
```

**Steps**:
1. Read `.gitignore`
2. Find line containing `.claude/`
3. Replace with selective entries above
4. Verify: `git status` should show `.claude/PROJECT.md`, `.claude/RULES.md`

**Validation**:
```bash
git status | grep ".claude/PROJECT.md"  # Should appear
git status | grep ".claude/settings.local.json"  # Should NOT appear
```

**Token Impact**: 0 tokens
**Files Modified**: `.gitignore`

---

### Task 1.2: Change Soft Language to Directives
**File**: `.claude/PROJECT.md`
**Issue**: 2 instances of "recommended" (RULE 12 violation)
**Compliance**: RULE 12

**Changes**:

**Change 1** - Line 186:
```markdown
# BEFORE
# Using helper script (recommended)

# AFTER
# MUST use helper script
```

**Change 2** - Line 609:
```markdown
# BEFORE
- Local agent execution via subprocess (recommended)

# AFTER
- MUST use local agent execution via subprocess
```

**Steps**:
1. Read `.claude/PROJECT.md`
2. Find line 186, replace "(recommended)" with ""
3. Change "Using helper script" to "MUST use helper script"
4. Find line 609, replace "(recommended)" with ""
5. Change "Local agent execution via subprocess" to "MUST use local agent execution via subprocess"

**Validation**:
```bash
./scripts/optimization/find-soft-language.sh | grep -c "recommended"  # Should be 0
```

**Token Impact**: 0 tokens (same length)
**Files Modified**: `.claude/PROJECT.md`

---

### Task 1.3: Create Skills Directory Structure
**File**: `.claude/skills/` (new directory)
**Issue**: No Skills architecture (RULE 14-17 violation)
**Compliance**: RULE 14, 15, 16, 17

**Implementation**:
```bash
mkdir -p .claude/skills
```

**Create**: `.claude/skills/README.md`

**Content**:
```markdown
# Obra Skills

Skills are specialized content loaded on-demand by Claude Code for specific tasks.

## Available Skills

1. **shell-enhancements** - WSL2 shell commands (35+) for Claude workflows
2. **development-tools** - LLM-optimized tools (tokei, ripgrep, fd, bat, etc.)
3. **testing-guidelines** - Pytest patterns and WSL2 crash prevention
4. **agile-workflow** - Epic/Story/Milestone management commands
5. **interactive-commands** - Interactive mode command reference

## Structure

Each Skill follows this structure:
```
.claude/skills/{skill-name}/
├─ SKILL.md           # Description + instructions
├─ examples/          # Code examples (optional)
└─ scripts/           # Automation scripts (optional)
```

## Metadata Format

SKILL.md MUST start with:
```markdown
# {Skill Name}

**Description**: [30-50 token description]
**Triggers**: [Keywords for invocation]
**Token Cost**: ~X tokens when loaded
**Dependencies**: [Required tools/configs]
```

## When Skills Load

- **ALWAYS**: Metadata (description, triggers) in startup context
- **ON-DEMAND**: Full content when user task matches triggers
- **NEVER**: Skills not relevant to current task

## Creating New Skills

MUST create Skill ONLY IF:
- Content >500 tokens AND
- Used <50% of sessions AND
- Self-contained domain

See: `docs/research/claude_code_project_optimization/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md` (RULE 14-17)
```

**Steps**:
1. Create directory: `.claude/skills/`
2. Write README.md with content above
3. Verify directory exists and is tracked by git

**Validation**:
```bash
ls -la .claude/skills/README.md  # Should exist
git status | grep ".claude/skills"  # Should appear (not ignored)
```

**Token Impact**: +250 tokens (metadata overhead for future Skills)
**Files Created**: `.claude/skills/README.md`

---

### Task 1.4: Archive OPTIMIZATION_SUMMARY.md
**File**: `.claude/OPTIMIZATION_SUMMARY.md`
**Issue**: Research notes (1,980 tokens) misplaced in `.claude/`
**Compliance**: File organization

**Implementation**:
```bash
mv .claude/OPTIMIZATION_SUMMARY.md docs/research/claude_code_project_optimization/
```

**Steps**:
1. Verify source file exists
2. Move to research directory
3. Verify no references to old location

**Validation**:
```bash
ls .claude/OPTIMIZATION_SUMMARY.md  # Should fail (file moved)
ls docs/research/claude_code_project_optimization/OPTIMIZATION_SUMMARY.md  # Should exist
```

**Token Impact**: 0 tokens (wasn't in startup context)
**Files Moved**: `.claude/OPTIMIZATION_SUMMARY.md` → `docs/research/claude_code_project_optimization/OPTIMIZATION_SUMMARY.md`

---

### Phase 1 Validation

**Run**:
```bash
./scripts/optimization/validate-structure.sh
./scripts/optimization/find-soft-language.sh
git status
```

**Expected**:
- ✅ .gitignore selective
- ✅ No soft language found
- ✅ .claude/skills/ directory exists
- ✅ Files tracked by git correctly

**Commit**:
```bash
git add .gitignore .claude/ docs/research/
git commit -m "fix: P0 critical optimizations (gitignore, soft language, Skills foundation)

- Fix .gitignore to selectively ignore .claude/ files (RULE 19)
- Change 'recommended' to 'MUST use' directive language (RULE 12)
- Create .claude/skills/ directory structure (RULE 14-17)
- Archive OPTIMIZATION_SUMMARY.md to research folder

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## PHASE 2: High-Impact Changes (P1) - THIS WEEK

**Duration**: 4 hours
**Goal**: Extract Skills, eliminate redundancy, compress examples
**Validation**: Startup context reduced by ~2,000 tokens

### Task 2.1: Extract shell-enhancements Skill
**Source**: `.claude/PROJECT.md` lines 321-413
**Target**: `.claude/skills/shell-enhancements/SKILL.md`
**Compliance**: RULE 14
**Token Savings**: 900 tokens from startup

**Implementation**:

**Step 1**: Create Skill directory and file
```bash
mkdir -p .claude/skills/shell-enhancements
```

**Step 2**: Create `.claude/skills/shell-enhancements/SKILL.md`

**Content**:
```markdown
# shell-enhancements

**Description**: WSL2 shell commands optimized for Claude Code workflows including context gathering (context, recent, todos), git shortcuts (gcom, gamend, gnew), and session management (save-context, diagnose). Includes 35+ commands with auto-detection for Python/Node/Rust/Go projects.

**Triggers**: WSL2, shell commands, bash, git workflow, session management, context gathering, gcom, gamend, recent, todos, save-context, diagnose, shell enhancements

**Token Cost**: ~900 tokens when loaded

**Dependencies**: WSL2 environment, bash, git, modern CLI tools (optional: fd, rg, bat)

---

[COPY CONTENT FROM PROJECT.md LINES 321-413 HERE - Shell Enhancements for LLM-Led Development section]
```

**Step 3**: Replace in `.claude/PROJECT.md` lines 321-413

**New content**:
```markdown
## Shell Enhancements for LLM-Led Development

WSL2 includes 35+ optimized commands for Claude Code workflows.

**See Skill**: `shell-enhancements` for complete command reference

**Quick Start**:
```bash
context              # Get project snapshot
recent 5             # Show recent files
todos                # Find TODO comments
gcom "msg"          # Stage all and commit
gnew branch         # Create and switch branch
```

**Full Documentation**: Invoke `shell-enhancements` Skill when needed
```

**Validation**:
```bash
wc -l .claude/skills/shell-enhancements/SKILL.md  # Should be ~100 lines
grep -c "shell-enhancements" .claude/PROJECT.md   # Should be 2-3 references
./scripts/optimization/token-counter.sh  # PROJECT.md should decrease by ~900 tokens
```

**Files Modified**: `.claude/PROJECT.md`
**Files Created**: `.claude/skills/shell-enhancements/SKILL.md`

---

### Task 2.2: Extract development-tools Skill
**Source**: `.claude/PROJECT.md` lines 72-116
**Target**: `.claude/skills/development-tools/SKILL.md`
**Compliance**: RULE 14
**Token Savings**: 500 tokens from startup

**Implementation**:

**Step 1**: Create Skill directory
```bash
mkdir -p .claude/skills/development-tools
```

**Step 2**: Create `.claude/skills/development-tools/SKILL.md`

**Content**:
```markdown
# development-tools

**Description**: LLM-optimized development tools including tokei (code stats), ripgrep (fast search), fd (find files), bat (syntax highlighting), jq/yq (JSON/YAML parsing), hyperfine (benchmarking), and httpie (HTTP requests). Includes comparison table to traditional Unix tools.

**Triggers**: tokei, ripgrep, rg, fd, bat, jq, yq, hyperfine, httpie, code analysis, search code, find files, parse JSON, development tools

**Token Cost**: ~500 tokens when loaded

**Dependencies**: Modern CLI tools (installation optional, Skill provides fallback guidance)

---

[COPY CONTENT FROM PROJECT.md LINES 72-116 HERE - LLM-Optimized Tools section]
```

**Step 3**: Replace in `.claude/PROJECT.md` lines 72-116

**New content**:
```markdown
### LLM-Optimized Tools (Installed)

Modern CLI tools optimized for AI-assisted development.

**See Skill**: `development-tools` for complete tool reference

**Quick Reference**:
- `tokei` - Code statistics
- `rg "pattern"` - Fast code search (10-100x faster than grep)
- `fd filename` - Find files (faster than find)
- `bat file.py` - View with syntax highlighting
- `jq '.key' data.json` - Parse JSON
- `yq '.key' file.yaml` - Parse YAML

**Full Guide**: Invoke `development-tools` Skill when needed
```

**Validation**:
```bash
wc -l .claude/skills/development-tools/SKILL.md  # Should be ~50 lines
./scripts/optimization/token-counter.sh  # PROJECT.md should decrease by ~500 tokens
```

**Files Modified**: `.claude/PROJECT.md`
**Files Created**: `.claude/skills/development-tools/SKILL.md`

---

### Task 2.3: Extract testing-guidelines Skill (Consolidate from Multiple Locations)
**Sources**:
- `CLAUDE.md` lines 125-153 (test patterns)
- `.claude/PROJECT.md` lines 206-231 (testing workflows)
- `.claude/PROJECT.md` lines 489-508 (testing patterns - DUPLICATE)
**Target**: `.claude/skills/testing-guidelines/SKILL.md`
**Compliance**: RULE 10 (eliminate redundancy), RULE 14
**Token Savings**: 600 tokens from startup

**Implementation**:

**Step 1**: Create Skill directory
```bash
mkdir -p .claude/skills/testing-guidelines
```

**Step 2**: Create `.claude/skills/testing-guidelines/SKILL.md`

**Content**:
```markdown
# testing-guidelines

**Description**: Comprehensive pytest patterns for Obra including WSL2 resource limits (0.5s sleep, 5 threads, 20KB memory), shared fixtures (test_config, fast_time), threading patterns, and crash prevention. Includes detailed examples of mocking, cleanup, and integration testing.

**Triggers**: pytest, testing, test patterns, fixtures, fast_time, WSL2 crashes, thread safety, test_config, threading, test guidelines

**Token Cost**: ~600 tokens when loaded

**Dependencies**: pytest, test fixtures from conftest.py

---

## Critical Resource Limits (WSL2 Crash Prevention)

**MUST follow these limits to prevent WSL2 kernel panics:**

- **Max sleep**: 0.5s per test
- **Max threads**: 5 per test
- **Max memory**: 20KB per test allocation
- **Mandatory**: `timeout=` on all thread joins
- **Mark heavy tests**: `@pytest.mark.slow`

**Why**: M2 testing caused WSL2 crashes from 75s cumulative sleeps, 25+ threads, 100KB+ memory.

**Documentation**: `docs/testing/TEST_GUIDELINES.md`

---

## Shared Fixtures

**ALWAYS use these fixtures from conftest.py:**

### test_config
```python
def test_orchestrator(test_config):
    """Use shared test configuration."""
    orchestrator = Orchestrator(config=test_config)
    assert orchestrator.config is not None
```

### fast_time
```python
def test_completion(fast_time):
    """Mock time for sleeps >0.5s."""
    monitor.mark_complete()
    time.sleep(2.0)  # Instant with fast_time mock
    assert monitor.is_complete()
```

---

## Threading Patterns

**MUST use timeouts on all joins:**

```python
def test_concurrent(test_config):
    """Test concurrent operations."""
    # Max 5 threads
    threads = [Thread(target=worker) for _ in range(3)]

    # Start all
    for t in threads:
        t.start()

    # MANDATORY: Join with timeout
    for t in threads:
        t.join(timeout=5.0)  # Prevents hangs
```

**BAD - No timeout**:
```python
for t in threads:
    t.join()  # NEVER do this - can hang forever
```

---

## Test Commands

**Run all tests**:
```bash
pytest
```

**Run with coverage**:
```bash
pytest --cov=src --cov-report=term
```

**Run only fast tests**:
```bash
pytest -m "not slow"
```

**Run specific module**:
```bash
pytest tests/test_state.py              # StateManager tests
pytest tests/test_orchestrator.py       # Orchestrator tests
```

**Auto-run on file changes**:
```bash
watchexec -e py pytest
```

---

## Test Organization

**Module tests** (M1-M10):
- `tests/test_state.py` - StateManager (M1)
- `tests/test_orchestrator.py` - Core orchestration (M6)
- `tests/test_validation.py` - Validation pipeline (M3)

**Integration tests**:
- `tests/test_integration_e2e.py` - End-to-end flows

**Mark slow tests**:
```python
@pytest.mark.slow
def test_heavy_operation():
    # Tests that exceed resource limits
    pass
```

---

## Common Patterns

### Cleanup
```python
def test_with_cleanup():
    resource = acquire_resource()
    try:
        # Test code
        pass
    finally:
        resource.cleanup()
```

### Mocking
```python
def test_with_mock(mocker):
    mock_llm = mocker.patch('src.core.orchestrator.LLMInterface')
    mock_llm.send_prompt.return_value = "response"
    # Test code
```

### Fixtures
```python
@pytest.fixture
def sample_task(test_config):
    state = StateManager(config=test_config)
    return state.create_task(project_id=1, title="Test", description="Test task")
```

---

## Error Prevention

**88% unit test coverage missed 6 bugs - MUST also write integration tests**

**Common mistakes**:
- ❌ Forget thread cleanup → WSL2 crash
- ❌ Long sleeps → WSL2 crash
- ❌ Too many threads → WSL2 crash
- ❌ Skip integration tests → Production bugs
- ❌ Assume mocks work like real code → Integration failures

**Best practices**:
- ✅ Use shared fixtures
- ✅ Mock time with fast_time
- ✅ Limit threads to 5
- ✅ Always use timeouts on joins
- ✅ Write both unit AND integration tests
```

**Step 3**: Update `CLAUDE.md` lines 125-153

**Replace with**:
```markdown
## Testing - CRITICAL Rules

**⚠️ READ `.claude/skills/testing-guidelines` BEFORE WRITING TESTS**

### Resource Limits (WSL2 Crash Prevention)
- **Max sleep**: 0.5s per test (use `fast_time` fixture for longer)
- **Max threads**: 5 per test (with mandatory `timeout=` on join)
- **Max memory**: 20KB per test
- **Mark heavy**: `@pytest.mark.slow`

### Why These Limits
M2 testing caused WSL2 crashes from 75s sleeps, 25+ threads, 100KB+ allocations.

**Detailed Patterns**: See `testing-guidelines` Skill
**Full Documentation**: `docs/testing/TEST_GUIDELINES.md`
```

**Step 4**: Update `.claude/PROJECT.md` lines 206-231

**Replace with**:
```markdown
### Testing Workflows

**CRITICAL**: Read `docs/testing/TEST_GUIDELINES.md` before writing tests!

**Run tests**:
```bash
pytest                           # All tests
pytest --cov=src --cov-report=term  # With coverage
pytest -m "not slow"             # Fast tests only
pytest tests/test_state.py       # Specific module
```

**Detailed Patterns**: See `testing-guidelines` Skill
```

**Step 5**: DELETE `.claude/PROJECT.md` lines 489-508 (duplicate content)

**Validation**:
```bash
wc -l .claude/skills/testing-guidelines/SKILL.md  # Should be ~120 lines
grep -c "testing-guidelines" CLAUDE.md  # Should be 1-2 references
grep -c "Testing Patterns" .claude/PROJECT.md  # Should be 0 (deleted duplicate)
./scripts/optimization/token-counter.sh  # Should show ~600 token savings
```

**Files Modified**: `CLAUDE.md`, `.claude/PROJECT.md`
**Files Created**: `.claude/skills/testing-guidelines/SKILL.md`

---

### Task 2.4: Compress 3 Longest Examples in CLAUDE.md
**Files**: `CLAUDE.md`
**Issue**: 3 examples exceed 10-line limit (RULE 13)
**Token Savings**: ~150 tokens

#### Example 1: CLAUDE.md lines 139-153 (13 lines → 8 lines)

**BEFORE**:
```python
# Use shared fixture
def test_with_config(test_config):
    orchestrator = Orchestrator(config=test_config)

# Mock time for long sleeps
def test_completion(fast_time):
    time.sleep(2.0)  # Instant with fast_time

# Threads with timeouts
def test_concurrent():
    threads = [Thread(target=work) for _ in range(3)]  # Max 5
    for t in threads: t.start()
    for t in threads: t.join(timeout=5.0)  # MANDATORY
```

**AFTER**:
```python
# Use fixtures: test_config, fast_time
def test_with_config(test_config):
    orch = Orchestrator(config=test_config)

def test_concurrent():
    threads = [Thread(target=work) for _ in range(3)]  # Max 5
    [t.start() for t in threads]; [t.join(timeout=5.0) for t in threads]
```

---

#### Example 2: CLAUDE.md lines 240-252 (11 lines → 8 lines)

**BEFORE**:
```
User → NL Processing → Orchestrator → StateManager → Task
                                ↓
                        StructuredPromptBuilder
                                ↓
                        Agent (fresh session)
                                ↓
                        Validation Pipeline (3 stages)
                                ↓
                        DecisionEngine → Action
                                ↓
                        StateManager → Git (optional)
```

**AFTER**:
```
User → NL Processing → Orchestrator → StateManager → Task
          ↓
    PromptBuilder → Agent → Validation(3) → Decision → StateManager/Git

Details: .claude/PROJECT.md (Architecture section)
```

---

#### Example 3: CLAUDE.md lines 280-295 (14 lines → 10 lines)

**BEFORE**:
```python
# StateManager access (always through orchestrator)
state = orchestrator.state_manager
task = state.create_task(project_id=1, title="...", description="...")

# Plugin loading
agent = AgentRegistry.get(config.get('agent.type'))()
llm = LLMRegistry.get(config.get('llm.type'))()

# Configuration
config = Config.load('config/config.yaml')

# Testing
pytest --cov=src --cov-report=term  # With coverage
pytest -m "not slow"                # Fast tests only
```

**AFTER**:
```python
# StateManager, plugins, config
state = orchestrator.state_manager
task = state.create_task(project_id=1, title="...", description="...")
agent = AgentRegistry.get(config.get('agent.type'))()
config = Config.load('config/config.yaml')

# Testing
pytest --cov=src --cov-report=term  # Coverage
pytest -m "not slow"                # Fast only
```

**Validation**:
```bash
./scripts/optimization/find-long-examples.sh  # Should show 3 fewer violations in CLAUDE.md
```

**Files Modified**: `CLAUDE.md`

---

### Task 2.5: Eliminate Testing Redundancy
**Already completed in Task 2.3** - Testing patterns consolidated into Skill, duplicates removed.

---

### Phase 2 Validation

**Run**:
```bash
./scripts/optimization/token-counter.sh
./scripts/optimization/find-long-examples.sh
./scripts/optimization/validate-structure.sh
```

**Expected**:
- ✅ PROJECT.md reduced by ~1,400 tokens
- ✅ CLAUDE.md reduced by ~150 tokens
- ✅ 3 Skills created with metadata
- ✅ Long examples in CLAUDE.md: 14 → 11 (3 compressed)
- ✅ No redundant testing content

**Commit**:
```bash
git add .claude/ CLAUDE.md
git commit -m "feat: P1 high-impact optimizations (Skills extraction, example compression)

- Extract shell-enhancements Skill (900 tokens → on-demand)
- Extract development-tools Skill (500 tokens → on-demand)
- Extract testing-guidelines Skill (600 tokens → on-demand, eliminate redundancy)
- Compress 3 longest examples in CLAUDE.md (13→8, 11→8, 14→10 lines)
- Reduce startup context by ~1,950 tokens

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## PHASE 3: Expansion & Optimization (P2) - THIS MONTH

**Duration**: 3 hours
**Goal**: Complete Skills, expand files to targets, achieve 100% compliance
**Validation**: 27/27 rules passing

### Task 3.1: Create agile-workflow Skill
**Source**: `.claude/PROJECT.md` lines 303-319
**Target**: `.claude/skills/agile-workflow/SKILL.md`
**Token Savings**: 200 tokens

[Implementation follows same pattern as Phase 2 Skills]

---

### Task 3.2: Create interactive-commands Skill
**Sources**: `CLAUDE.md` lines 196-211 + `.claude/PROJECT.md` lines 284-301
**Target**: `.claude/skills/interactive-commands/SKILL.md`
**Token Savings**: 250 tokens

[Implementation follows same pattern as Phase 2 Skills]

---

### Task 3.3: Compress Remaining Long Examples in PROJECT.md
**Target**: 5 longest examples (24, 18, 18, 16, 15 lines)
**Token Savings**: 600-800 tokens

[Compress using same techniques as Phase 2]

---

### Task 3.4: Expand CLAUDE.md to Target Range
**Current**: 1,734 tokens
**Target**: 3,000-5,000 tokens
**Addition**: +1,200 tokens

**Add these sections**:

1. Skills Architecture Explanation (+200 tokens)
2. Context Management Rules (+300 tokens)
3. Rewind/Checkpoint Best Practices (+200 tokens)
4. MCP Server Integration (+200 tokens)
5. Subagent Delegation Patterns (+300 tokens)

[Detailed content in action plan document]

---

### Task 3.5: Expand RULES.md to Target Range
**Current**: 1,136 tokens
**Target**: 2,000-4,000 tokens
**Addition**: +864 tokens

**Add**:
1. Advanced StateManager patterns (+400 tokens)
2. Common error fixes (+300 tokens)
3. Debug checklist (+164 tokens)

[Detailed content in action plan document]

---

### Phase 3 Validation

**Final Validation**:
```bash
./scripts/optimization/validate-structure.sh
```

**Expected**:
- ✅ 27/27 rules passing (100% compliance)
- ✅ CLAUDE.md: 2,900-3,000 tokens
- ✅ PROJECT.md: 5,500-6,500 tokens
- ✅ RULES.md: 2,000 tokens
- ✅ 7 Skills created
- ✅ Skills metadata: 350 tokens
- ✅ Total startup: 6,500-7,000 tokens
- ✅ Skills on-demand: 2,900 tokens
- ✅ No long examples >10 lines
- ✅ No soft language
- ✅ .gitignore selective

**Final Commit**:
```bash
git add .claude/ CLAUDE.md docs/
git commit -m "feat: P2 optimization complete - 100% rule compliance

- Create agile-workflow and interactive-commands Skills
- Compress remaining long examples in PROJECT.md
- Expand CLAUDE.md with Skills architecture, context management, Rewind, MCP, subagents (+1,200 tokens)
- Expand RULES.md with patterns, errors, debug checklist (+864 tokens)
- Achieve 27/27 rule compliance (100%)
- Total managed: 9,400 tokens (6,500 startup + 2,900 on-demand)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Success Metrics

### Before Implementation
```
CLAUDE.md:      1,734 tokens  ⚠️ Below target
PROJECT.md:     3,073 tokens  ⚠️ Below target
RULES.md:       1,136 tokens  ⚠️ Below target
Skills:             0 tokens  ❌ Missing
TOTAL:          5,943 tokens

Compliance: 15/27 (55.6%)
Long examples: 17
Soft language: 2
.gitignore: ❌ Too broad
```

### After Phase 1 (Today)
```
CLAUDE.md:      1,734 tokens  (no change)
PROJECT.md:     3,073 tokens  (no change)
RULES.md:       1,136 tokens  (no change)
Skills:           250 tokens  (metadata only)
TOTAL:          6,193 tokens

Fixes:
✅ .gitignore selective
✅ Soft language removed
✅ Skills foundation
```

### After Phase 2 (This Week)
```
CLAUDE.md:      1,584 tokens  (-150)
PROJECT.md:     1,623 tokens  (-1,450)
RULES.md:       1,136 tokens  (no change)
Skills:           250 tokens  (metadata, 3 Skills)
TOTAL:          4,593 tokens  (-1,350)

Skills on-demand: 2,000 tokens

Benefits:
✅ 3 Skills extracted
✅ Examples compressed
✅ Redundancy eliminated
```

### After Phase 3 (This Month)
```
CLAUDE.md:      2,934 tokens  (+1,350)
PROJECT.md:     1,623 tokens  (no change)
RULES.md:       2,000 tokens  (+864)
Skills:           350 tokens  (metadata, 7 Skills)
TOTAL:          6,907 tokens

Skills on-demand: 2,900 tokens
Total managed: 9,807 tokens

Achievements:
✅ 27/27 rules (100% compliance)
✅ All files in target ranges
✅ 7 Skills with progressive disclosure
✅ No violations
```

---

## Rollback Plan

If issues occur, rollback by phase:

**Phase 1 Rollback**:
```bash
git revert HEAD  # Undo P0 commit
```

**Phase 2 Rollback**:
```bash
git revert HEAD  # Undo P1 commit
git revert HEAD~1  # Also undo P0 if needed
```

**Phase 3 Rollback**:
```bash
git revert HEAD  # Undo P2 commit
# P1 and P0 remain (keep Skills)
```

**Complete Rollback**:
```bash
git log --oneline -5  # Find commit before optimizations
git reset --hard <commit-sha>  # Nuclear option
```

---

## Notes for Claude Code

**MUST read before starting**:
1. `docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_AUDIT_REPORT.md`
2. `docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_ACTION_PLAN.md`
3. `docs/research/claude_code_project_optimization/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md`

**Validation scripts**:
- Token counter: `./scripts/optimization/token-counter.sh`
- Soft language: `./scripts/optimization/find-soft-language.sh`
- Long examples: `./scripts/optimization/find-long-examples.sh`
- Full validation: `./scripts/optimization/validate-structure.sh`

**Execution approach**:
- ONE phase at a time
- VALIDATE after each task
- COMMIT after each phase
- RUN scripts before committing
- VERIFY git status shows correct files

**Token counting**:
- Use word count × 1.3 approximation
- Verify with token-counter.sh
- Check before/after each change

**Line numbers**:
- May shift after edits
- Re-read files to find current line numbers
- Use grep to find specific content

**Skills metadata format**:
- Description: 30-50 tokens
- Triggers: Comma-separated keywords
- Token cost: Estimated from word count × 1.3
- Dependencies: Required tools/configs
