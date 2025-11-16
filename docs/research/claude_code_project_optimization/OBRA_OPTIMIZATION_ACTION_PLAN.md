# OBRA Optimization Action Plan

**Project**: Obra (Claude Code Orchestrator)
**Date**: November 15, 2025
**Based On**: OBRA_OPTIMIZATION_AUDIT_REPORT.md

---

## Priority Overview

| Priority | Count | Est. Time | Token Impact | Completion Target |
|----------|-------|-----------|--------------|-------------------|
| **P0 - CRITICAL** | 3 actions | 30 min | -50 tokens, +compliance | Today |
| **P1 - HIGH IMPACT** | 6 actions | 4 hours | -2,600 tokens | This week |
| **P2 - OPTIMIZATION** | 5 actions | 3 hours | +1,500 tokens | This month |

---

## P0 - CRITICAL (Do Immediately - Today)

### P0-1: Fix .gitignore Configuration

**Issue**: `.gitignore` blocks ALL `.claude/` files instead of selective ignoring (RULE 19 violation)

**File**: `.gitignore`
**Current** (line ~1):
```gitignore
# Claude Code CLI
.claude/
```

**Fixed**:
```gitignore
# Claude Code CLI - local files only
.claude/settings.local.json
.claude/.cache/
.claude/logs/
```

**Implementation Steps**:
1. Open `.gitignore`
2. Replace `.claude/` with selective entries
3. Test: `git status` should show `.claude/PROJECT.md`, `.claude/RULES.md`, etc.
4. Commit: `git add .claude/PROJECT.md .claude/RULES.md .claude/commands/ && git commit -m "fix: Update .gitignore for selective .claude/ tracking"`

**Token Impact**: 0 tokens
**Time**: 2 minutes
**Benefits**: Enables team collaboration on Skills and configs

---

### P0-2: Change Soft Language to Directives

**Issue**: 2 instances of "recommended" instead of directive language (RULE 12 violation)

**File 1**: `.claude/PROJECT.md`
**Line**: 186
**Before**:
```markdown
# Using helper script (recommended)
```

**After**:
```markdown
# MUST use helper script
```

---

**File 2**: `.claude/PROJECT.md`
**Line**: 609
**Before**:
```markdown
- Local agent execution via subprocess (recommended)
```

**After**:
```markdown
- MUST use local agent execution via subprocess
```

**Implementation Steps**:
1. Open `.claude/PROJECT.md`
2. Find and replace "recommended" with directive language
3. Verify context supports MUST (soften if truly optional)
4. Test: Search for remaining soft language: `grep -n "should\|consider\|recommend\|might" .claude/*.md CLAUDE.md`

**Token Impact**: 0 tokens (same length)
**Time**: 5 minutes
**Benefits**: RULE 12 compliance, clearer directives

---

### P0-3: Create .claude/skills/ Directory Structure

**Issue**: No Skills architecture implemented (RULE 14, 15, 16, 17 violation)

**Current**: Directory doesn't exist
**Target**: Proper Skills structure

**Implementation Steps**:
1. Create directory: `mkdir -p .claude/skills`
2. Create README: `.claude/skills/README.md` with overview
3. Verify in .gitignore (after P0-1): `.claude/skills/` NOT ignored

```bash
mkdir -p .claude/skills
cat > .claude/skills/README.md << 'EOF'
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

SKILL.md must start with:
```markdown
# {Skill Name}

**Description**: [30-50 token description]
**Triggers**: [Keywords for invocation]
**Token Cost**: ~X tokens when loaded
**Dependencies**: [Required tools/configs]
```

See: `docs/research/claude_code_project_optimization/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md` (RULE 14-17)
EOF
```

**Token Impact**: +250 tokens (Skills metadata overhead)
**Time**: 5 minutes
**Benefits**: Foundation for progressive disclosure pattern

---

## P1 - HIGH IMPACT (Do This Week)

### P1-1: Extract shell-enhancements Skill

**Issue**: 900 tokens of specialized WSL2 commands in PROJECT.md used <30% of sessions

**Source**: `.claude/PROJECT.md` lines 321-413
**Target**: `.claude/skills/shell-enhancements/SKILL.md`

**Before** (in PROJECT.md):
```markdown
## Shell Enhancements for LLM-Led Development

The WSL2 environment includes 35+ commands optimized for Claude Code workflows.

### Before Starting Claude Code Sessions
...
[92 lines of specialized commands]
```

**After** (in SKILL.md):
```markdown
# shell-enhancements

**Description**: WSL2 shell commands optimized for Claude Code workflows including context gathering (context, recent, todos), git shortcuts (gcom, gamend, gnew), and session management (save-context, diagnose). Includes 35+ commands with auto-detection for Python/Node/Rust/Go projects.

**Triggers**: WSL2, shell commands, bash, git workflow, session management, context gathering, gcom, gamend, recent, todos, save-context

**Token Cost**: ~900 tokens when loaded

**Dependencies**: WSL2 environment, bash, git, modern CLI tools (optional: fd, rg, bat)

## Commands Overview

[Content from PROJECT.md lines 321-413 goes here]
```

**After** (in PROJECT.md lines 321):
```markdown
## Shell Enhancements for LLM-Led Development

WSL2 includes 35+ optimized commands for Claude Code workflows.

**See Skill**: `shell-enhancements` for complete command reference

**Quick Start**:
```bash
context              # Get project snapshot
recent 5             # Show recent files
todos                # Find TODO comments
```

**Full Documentation**: Invoke `shell-enhancements` Skill
```

**Implementation Steps**:
1. Create `.claude/skills/shell-enhancements/SKILL.md`
2. Copy content from PROJECT.md:321-413
3. Add proper Skill metadata header
4. Replace PROJECT.md section with short summary + Skill reference
5. Test invocation: Claude should load when user mentions "shell commands"

**Token Savings**: 900 tokens from startup → on-demand loading
**Time**: 30 minutes
**Benefits**: Largest single token savings

---

### P1-2: Extract development-tools Skill

**Issue**: 500 tokens of tool reference material in PROJECT.md used <40% of sessions

**Source**: `.claude/PROJECT.md` lines 72-116
**Target**: `.claude/skills/development-tools/SKILL.md`

**Skill Metadata**:
```markdown
# development-tools

**Description**: LLM-optimized development tools including tokei (code stats), ripgrep (fast search), fd (find files), bat (syntax highlighting), jq/yq (JSON/YAML parsing), hyperfine (benchmarking), and httpie (HTTP requests). Includes comparison table to traditional Unix tools.

**Triggers**: tokei, ripgrep, rg, fd, bat, jq, yq, hyperfine, httpie, code analysis, search code, find files, parse JSON

**Token Cost**: ~500 tokens when loaded

**Dependencies**: Tools should be installed but Skill provides fallback guidance
```

**PROJECT.md Replacement** (lines 72):
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

**Full Guide**: Invoke `development-tools` Skill
```

**Token Savings**: 500 tokens
**Time**: 20 minutes

---

### P1-3: Extract testing-guidelines Skill

**Issue**: Testing patterns duplicated across CLAUDE.md and PROJECT.md, detailed patterns not needed every session

**Sources**:
- `CLAUDE.md` lines 125-153
- `.claude/PROJECT.md` lines 206-231
- `.claude/PROJECT.md` lines 489-508

**Target**: `.claude/skills/testing-guidelines/SKILL.md`

**Skill Metadata**:
```markdown
# testing-guidelines

**Description**: Comprehensive pytest patterns for Obra including WSL2 resource limits (0.5s sleep, 5 threads, 20KB memory), shared fixtures (test_config, fast_time), threading patterns, and crash prevention. Includes detailed examples of mocking, cleanup, and integration testing.

**Triggers**: pytest, testing, test patterns, fixtures, fast_time, WSL2 crashes, thread safety, test_config, threading

**Token Cost**: ~600 tokens when loaded

**Dependencies**: pytest, test fixtures from conftest.py
```

**CLAUDE.md Replacement** (lines 125-153):
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

**PROJECT.md Changes**:
- Remove lines 489-508 (testing patterns)
- Update lines 206-231 to reference Skill for detailed patterns

**Token Savings**: 600 tokens (consolidated from multiple locations)
**Time**: 40 minutes
**Benefits**: Eliminates redundancy, centralizes testing knowledge

---

### P1-4: Compress 3 Longest Examples in CLAUDE.md

**Issue**: 3 code examples exceed 10-line limit (RULE 13 violation)

#### Example 1: CLAUDE.md lines 139-153 (13 lines → 8 lines)

**Before**:
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

**After**:
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

**Before**:
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

**After**:
```
User → NL Processing → Orchestrator → StateManager → Task
          ↓
    PromptBuilder → Agent → Validation(3) → Decision → StateManager/Git

Details: .claude/PROJECT.md (Architecture section)
```

---

#### Example 3: CLAUDE.md lines 280-295 (14 lines → 10 lines)

**Before**:
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

**After**:
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

**Token Savings**: ~150 tokens across 3 examples
**Time**: 20 minutes
**Benefits**: RULE 13 compliance, faster parsing

---

### P1-5: Eliminate Testing Redundancy

**Issue**: Testing patterns appear in CLAUDE.md, PROJECT.md (2 locations), and should be in Skill

**Consolidated in**: `.claude/skills/testing-guidelines/SKILL.md` (P1-3)

**Remove from**:
- `.claude/PROJECT.md` lines 489-508 (Testing Patterns section)

**Simplify in**:
- `CLAUDE.md` lines 125-153 (keep critical limits, reference Skill)
- `.claude/PROJECT.md` lines 206-231 (keep commands, reference Skill)

**Implementation**:
1. Complete P1-3 first (create Skill)
2. Edit CLAUDE.md to compress testing section
3. Edit PROJECT.md to reference Skill for detailed patterns
4. Remove PROJECT.md:489-508 entirely

**Token Savings**: 400 tokens
**Time**: 15 minutes
**Benefits**: Single source of truth for testing knowledge

---

### P1-6: Archive OPTIMIZATION_SUMMARY.md

**Issue**: `.claude/OPTIMIZATION_SUMMARY.md` is research notes (1,980 tokens) not needed in `.claude/`

**Current**: `.claude/OPTIMIZATION_SUMMARY.md` (389 lines, 1,523 words)
**Target**: `docs/research/claude_code_project_optimization/OPTIMIZATION_SUMMARY.md`

**Implementation**:
```bash
# Move file
mv .claude/OPTIMIZATION_SUMMARY.md docs/research/claude_code_project_optimization/

# Update any references (unlikely)
rg "OPTIMIZATION_SUMMARY" CLAUDE.md .claude/

# Commit
git add .claude/ docs/research/
git commit -m "docs: Move optimization summary to research folder"
```

**Token Savings**: 0 (file wasn't in startup context)
**Time**: 2 minutes
**Benefits**: Cleaner .claude/ directory, better organization

---

## P2 - OPTIMIZATION (Do This Month)

### P2-1: Create agile-workflow Skill

**Source**: `.claude/PROJECT.md` lines 303-319
**Size**: 200 tokens (below threshold but useful for organization)

**Skill Metadata**:
```markdown
# agile-workflow

**Description**: Epic, Story, Milestone management commands for Agile/Scrum workflows including creation (epic create, story create, milestone create), listing, execution, and completion tracking. Supports hierarchical task organization.

**Triggers**: epic, story, milestone, agile, scrum, task hierarchy, backlog, sprint

**Token Cost**: ~200 tokens when loaded

**Dependencies**: Obra CLI, StateManager
```

**PROJECT.md Replacement**:
```markdown
## Agile Workflow (v1.3.0)

Epic/Story/Milestone management for Agile/Scrum workflows.

**See Skill**: `agile-workflow` for complete command reference

**Quick Commands**:
```bash
python -m src.cli epic create "Title" --project 1
python -m src.cli story create "Title" --epic 1 --project 1
python -m src.cli milestone create "Title" --project 1
```

**Full Guide**: Invoke `agile-workflow` Skill
```

**Token Savings**: 200 tokens
**Time**: 15 minutes

---

### P2-2: Create interactive-commands Skill

**Sources**:
- `CLAUDE.md` lines 196-211
- `.claude/PROJECT.md` lines 284-301

**Consolidated Size**: 250 tokens

**Skill Metadata**:
```markdown
# interactive-commands

**Description**: Interactive mode command reference including natural language defaults (no / prefix), system commands (/help, /status, /pause, /resume, /stop, /to-impl, /override-decision), and command injection points during execution.

**Triggers**: interactive mode, /help, /status, /pause, /to-impl, command injection, interactive, /commands

**Token Cost**: ~250 tokens when loaded

**Dependencies**: Interactive CLI mode (python -m src.cli interactive)
```

**CLAUDE.md Replacement** (lines 196-211):
```markdown
## Interactive Mode (v1.5.0 UX)

**Natural text** (no `/`) defaults to orchestrator.
**System commands** require `/` prefix.

**See Skill**: `interactive-commands` for complete reference

**Key Commands**: `/help`, `/status`, `/pause`, `/resume`, `/to-impl <msg>`
```

**TOKEN SAVINGS**: 250 tokens
**Time**: 20 minutes

---

### P2-3: Compress Remaining Long Examples in PROJECT.md

**Issue**: 14 examples in PROJECT.md exceed 10-line limit

**Target**: Compress top 5 longest examples (lines 24+, 18+, 18+, 16+, 15+)

#### Example 1: PROJECT.md lines 77-102 (24 lines → 10 lines)

Large tool comparison table - compress to bullets:

**Before**: 24-line table
**After**:
```markdown
**Key Tools**:
- **Search**: `rg` (10-100x faster than grep)
- **Find**: `fd` (faster, better syntax)
- **View**: `bat` (syntax highlighting)
- **Parse**: `jq` (JSON), `yq` (YAML)
- **Benchmark**: `hyperfine` (statistical analysis)
- **HTTP**: `http`/httpie (readable syntax)
- **Git**: `lazygit` (visual TUI)

**Full Guide**: See `development-tools` Skill
```

#### Example 2: PROJECT.md lines 466-484 (18 lines → 10 lines)

Configuration patterns - compress:

**Before**: 18 lines of code examples
**After**:
```python
# Load config and access nested values
config = Config.load('config.yaml')
agent = AgentRegistry.get(config.get('agent.type'))()

# StateManager access
state = orchestrator.state_manager
task = state.create_task(project_id=1, title="...", description="...")

# Profile validation
if profile in ProfileManager.list_profiles():
    profile = ProfileManager.load_profile(profile)
```

**Token Savings**: 600-800 tokens across 5 examples
**Time**: 45 minutes

---

### P2-4: Expand CLAUDE.md to Target Range

**Issue**: CLAUDE.md at 1,734 tokens, target is 3,000-5,000 tokens

**Missing Critical Content**:

1. **Skills Architecture Explanation** (+200 tokens):
```markdown
## Skills Architecture (v2.0)

**Progressive Disclosure**: Skills load on-demand when Claude determines relevance.

### When Skills Load
- **ALWAYS**: Metadata (description, triggers) in startup context
- **ON-DEMAND**: Full content when user task matches triggers
- **NEVER**: Skills not relevant to current task

### How to Invoke Skills
- Natural language mentions trigger keywords
- Explicit: "See shell-enhancements Skill"
- Claude auto-loads based on task analysis

**Available Skills**: See `.claude/skills/README.md`
```

2. **Context Management Rules** (+300 tokens):
```markdown
## Context Management

### Session Refresh Triggers (ADR-018)
MUST start new session IF:
- Context >80% capacity (monitoring enabled)
- Task type changed significantly
- Previous task complete and new task unrelated
- Confusion signals detected (repeated clarifications)

### Context Compaction
WHEN context >60% full:
- Remove outdated tool results
- Summarize completed subtasks
- NEVER remove active task context

### Monitoring
- Track token usage per task
- Monitor context zones (green <60%, yellow 60-85%, red >85%)
- Log handoff events in production logger
```

3. **Rewind/Checkpoint Best Practices** (+200 tokens):
```markdown
## Rewind & Checkpoints

### When to Create Checkpoints
MUST checkpoint BEFORE:
- Major refactoring (>500 lines changed)
- Architectural changes (new components/patterns)
- Dependency updates (breaking changes risk)
- Risky operations (schema migrations, bulk updates)

ALWAYS checkpoint AFTER:
- Successful milestone achievement
- Working feature implementation
- Passing test suite restoration

### How to Use Rewind
1. Double-tap ESC → Activate Rewind UI
2. Select checkpoint from timeline
3. Claude restores conversation + file states
4. Review diffs before accepting
```

4. **MCP Server Integration** (+200 tokens):
```markdown
## MCP Server Integration

### Setup
Configure in `.mcp.json` (project root):
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
    }
  }
}
```

### Usage
- MCP tools available automatically
- Claude invokes when needed (PR creation, issue search, repo stats)
- Results count toward context budget
- Tokens: ~100-500 per MCP operation
```

5. **Subagent Delegation Patterns** (+300 tokens):
```markdown
## Subagent Delegation

### When to Create Subagents
CREATE subagent IF:
- Specialized task domain (testing, docs, deployment)
- Different tool permissions needed
- Isolated context beneficial
- Parallel work possible (multiple PRs, test suites)

DO NOT create IF:
- Main orchestrator can handle
- Overhead exceeds benefit
- Context sharing needed

### Configuration Pattern
`.claude/agents/{name}/config.json`:
```json
{
  "name": "test-agent",
  "model": "claude-haiku-4-5-20250919",  // Cheaper for routine tasks
  "system_prompt": ".claude/agents/test-agent/system.md",
  "tools": ["bash", "edit_file"],  // Restricted permissions
  "context": ["tests/", ".claude/skills/testing/"]
}
```

**Token Addition**: +1,200 tokens → CLAUDE.md reaches ~2,934 tokens (within 3K-5K target)
**Time**: 1 hour

---

### P2-5: Expand RULES.md to Target Range

**Issue**: RULES.md at 1,136 tokens, target is 2,000-4,000 tokens

**Additions**:

1. **More Pattern Examples** (+400 tokens):
```markdown
## Advanced StateManager Patterns

### Atomic Operations
# Good: Single transaction
with state.transaction():
    task = state.create_task(project_id=1, title="...")
    state.update_task(task_id=task.task_id, status=TaskStatus.IN_PROGRESS)

# Bad: Multiple commits
task = state.create_task(...)  # commit 1
state.update_task(...)  # commit 2

### Bulk Operations
# Efficient: Batch updates
tasks = state.get_tasks(project_id=1)
updates = [{'task_id': t.task_id, 'status': TaskStatus.COMPLETED} for t in tasks]
state.bulk_update_tasks(updates)
```

2. **Common Error Messages and Fixes** (+300 tokens):
```markdown
## Common Errors Quick Fix

| Error | Cause | Fix |
|-------|-------|-----|
| `StateManager not initialized` | Used `Config()` not `Config.load()` | Load config from file |
| `Agent not found in registry` | Typo in config.agent.type | Check registered name |
| `Session lock conflict` | Reused session | Fresh session per iteration |
| `WSL2 kernel panic` | Test resource limits exceeded | Follow TEST_GUIDELINES.md |
| `LLM connection timeout` | Network/Ollama down | `orchestrator.reconnect_llm()` |
| `Profile not found` | Profile doesn't exist | Validate before loading |
```

3. **Quick Debugging Checklist** (+164 tokens):
```markdown
## Debug Checklist

### When Task Fails
- [ ] Check LLM connection: `orchestrator.check_llm_available()`
- [ ] Review logs: `tail -f ~/obra-runtime/logs/production.jsonl`
- [ ] Verify StateManager state: `state.get_task(task_id)`
- [ ] Check validation pipeline: ResponseValidator → QualityController → ConfidenceScorer

### When Tests Fail
- [ ] Resource limits OK? (0.5s sleep, 5 threads, 20KB)
- [ ] Fixtures loaded? (test_config, fast_time)
- [ ] Thread cleanup? (join with timeout)
- [ ] Integration vs unit? (88% unit coverage missed 6 bugs)
```

**Token Addition**: +864 tokens → RULES.md reaches ~2,000 tokens (within target)
**Time**: 30 minutes

---

## Implementation Roadmap

### Today (30 minutes)
1. ✅ P0-1: Fix .gitignore (2 min)
2. ✅ P0-2: Change soft language (5 min)
3. ✅ P0-3: Create Skills directory (5 min)
4. ✅ P1-6: Archive OPTIMIZATION_SUMMARY.md (2 min)
5. ✅ Test git tracking: `git status` should show `.claude/skills/`

### This Week (4 hours)
6. ✅ P1-1: Extract shell-enhancements Skill (30 min)
7. ✅ P1-2: Extract development-tools Skill (20 min)
8. ✅ P1-3: Extract testing-guidelines Skill (40 min)
9. ✅ P1-4: Compress 3 longest examples in CLAUDE.md (20 min)
10. ✅ P1-5: Eliminate testing redundancy (15 min)
11. ✅ Test: Claude session with Skills invocation

### This Month (3 hours)
12. ✅ P2-1: Create agile-workflow Skill (15 min)
13. ✅ P2-2: Create interactive-commands Skill (20 min)
14. ✅ P2-3: Compress 5 longest examples in PROJECT.md (45 min)
15. ✅ P2-4: Expand CLAUDE.md to target (1 hour)
16. ✅ P2-5: Expand RULES.md to target (30 min)
17. ✅ Final validation: Run token counter script

---

## Expected Results

### Before Optimization
```
CLAUDE.md:     1,734 tokens  (below target)
PROJECT.md:    3,073 tokens  (below target)
RULES.md:      1,136 tokens  (below target)
Skills:            0 tokens
TOTAL:         5,943 tokens

Issues:
- 17 long examples
- Redundant content
- No Skills architecture
- Broad .gitignore
```

### After P0 (Critical - Today)
```
CLAUDE.md:     1,734 tokens  (no change)
PROJECT.md:    3,073 tokens  (no change)
RULES.md:      1,136 tokens  (no change)
Skills:          250 tokens  (metadata only)
TOTAL:         6,193 tokens  (+250)

Fixes:
✅ .gitignore selective
✅ Directive language
✅ Skills foundation
```

### After P1 (High Impact - This Week)
```
CLAUDE.md:     1,584 tokens  (-150: compressed examples)
PROJECT.md:    1,023 tokens  (-2,050: extracted Skills)
RULES.md:      1,136 tokens  (no change)
Skills:          250 tokens  (metadata)
TOTAL:         3,993 tokens  (-1,950 from startup)

Skills On-Demand: 2,450 tokens

Fixes:
✅ Skills extracted
✅ Examples compressed
✅ Redundancy eliminated
✅ Archive cleaned
```

### After P2 (Optimization - This Month)
```
CLAUDE.md:     2,934 tokens  (+1,200: expanded content)
PROJECT.md:    1,623 tokens  (+600: better examples, - more Skills)
RULES.md:      2,000 tokens  (+864: expanded patterns)
Skills:          350 tokens  (metadata for 7 Skills)
TOTAL:         6,907 tokens  (optimal structure)

Skills On-Demand: 2,900 tokens

Benefits:
✅ All files in target ranges
✅ Complete critical content
✅ 7 Skills for progressive disclosure
✅ Optimal token distribution
✅ RULE compliance: 27/27
```

---

## Validation Checklist

After completing all actions:

**File Size Compliance**:
- [ ] CLAUDE.md: 300-400 lines, 3K-5K tokens ✅
- [ ] PROJECT.md: 400-700 lines, 5K-9K tokens ✅
- [ ] RULES.md: 2K-4K tokens ✅
- [ ] Total startup: <15K tokens ✅
- [ ] Skills metadata: 300-500 tokens ✅

**Content Quality**:
- [ ] No redundancy across files (RULE 10) ✅
- [ ] All bullets, no prose (RULE 11) ✅
- [ ] Directive language (RULE 12) ✅
- [ ] Examples ≤10 lines (RULE 13) ✅
- [ ] Skills created for >500 token specialized content (RULE 14) ✅

**Infrastructure**:
- [ ] .gitignore selective (RULE 19) ✅
- [ ] Skills have proper metadata (RULE 15-17) ✅
- [ ] .claude/skills/ directory exists ✅

**Testing**:
- [ ] Claude session loads successfully
- [ ] Skills invoke when triggered
- [ ] Token budget measured with script
- [ ] All files committed to git

---

**Next Steps**:
1. Execute P0 actions today
2. Schedule P1 for this week
3. Generate implementation scripts (OUTPUT 3)
