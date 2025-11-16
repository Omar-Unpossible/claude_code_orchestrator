# Machine-Optimized Implementation Guide
# Obra Claude Code Optimization - Autonomous Execution Protocol

**Target**: Claude Code LLM (autonomous execution)
**Format**: Directive commands, no prose, clear validation
**Phases**: 3 (P0 → P1 → P2)

---

## PHASE 0: INITIALIZATION

### STEP 0.1: Read Context Documents
READ in this order:
1. `docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_AUDIT_REPORT.md`
2. `docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_ACTION_PLAN.md`
3. `docs/research/claude_code_project_optimization/IMPLEMENTATION_PLAN.md`

### STEP 0.2: Verify Scripts Executable
```bash
ls -lh scripts/optimization/*.sh
```
IF not executable:
```bash
chmod +x scripts/optimization/*.sh
```

### STEP 0.3: Run Baseline Measurement
```bash
./scripts/optimization/token-counter.sh > /tmp/baseline-tokens.txt
./scripts/optimization/find-soft-language.sh > /tmp/baseline-soft-lang.txt
./scripts/optimization/find-long-examples.sh > /tmp/baseline-long-examples.txt
```

VERIFY baseline recorded.

---

## PHASE 1: CRITICAL FIXES (P0)

**Goal**: Fix .gitignore, soft language, create Skills directory
**Time**: 30 minutes
**Validation**: validate-structure.sh passes P0 checks

### TASK P0.1: Fix .gitignore

READ: `.gitignore`
FIND line: `.claude/`
REPLACE with:
```gitignore
# Claude Code CLI - local files only
.claude/settings.local.json
.claude/.cache/
.claude/logs/
```

VALIDATE:
```bash
git status | grep -c ".claude/PROJECT.md"  # Output: 1
git status | grep ".claude/settings.local.json"  # Output: empty
```

IF validation FAILS → STOP, report error

---

### TASK P0.2: Change Soft Language

READ: `.claude/PROJECT.md`

CHANGE 1:
- FIND line ~186: `# Using helper script (recommended)`
- REPLACE: `# MUST use helper script`

CHANGE 2:
- FIND line ~609: `- Local agent execution via subprocess (recommended)`
- REPLACE: `- MUST use local agent execution via subprocess`

VALIDATE:
```bash
./scripts/optimization/find-soft-language.sh | grep -c "recommended"  # Output: 0
```

IF validation FAILS → STOP, report error

---

### TASK P0.3: Create Skills Directory

EXECUTE:
```bash
mkdir -p .claude/skills
```

WRITE: `.claude/skills/README.md`
CONTENT:
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

VALIDATE:
```bash
ls .claude/skills/README.md  # Must exist
git status | grep ".claude/skills"  # Must appear (not ignored)
```

IF validation FAILS → STOP, report error

---

### TASK P0.4: Archive OPTIMIZATION_SUMMARY.md

EXECUTE:
```bash
mv .claude/OPTIMIZATION_SUMMARY.md docs/research/claude_code_project_optimization/
```

VALIDATE:
```bash
ls .claude/OPTIMIZATION_SUMMARY.md 2>&1 | grep -c "No such file"  # Output: 1
ls docs/research/claude_code_project_optimization/OPTIMIZATION_SUMMARY.md  # Must exist
```

IF validation FAILS → STOP, report error

---

### PHASE 1 VALIDATION

RUN:
```bash
./scripts/optimization/validate-structure.sh
git status
```

VERIFY:
- ✅ .gitignore selective (not blocking .claude/PROJECT.md)
- ✅ No soft language violations
- ✅ .claude/skills/ exists and tracked
- ✅ All changes staged correctly

IF ANY check FAILS → STOP, report error

---

### PHASE 1 COMMIT

EXECUTE:
```bash
git add .gitignore .claude/skills/ docs/research/claude_code_project_optimization/OPTIMIZATION_SUMMARY.md
git add .claude/PROJECT.md  # If soft language changed

git commit -m "fix: P0 critical optimizations (gitignore, soft language, Skills foundation)

- Fix .gitignore to selectively ignore .claude/ files (RULE 19)
- Change 'recommended' to 'MUST use' directive language (RULE 12)
- Create .claude/skills/ directory structure (RULE 14-17)
- Archive OPTIMIZATION_SUMMARY.md to research folder

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

VALIDATE:
```bash
git log -1 --oneline | grep "P0 critical optimizations"  # Must match
git status  # Should be clean or show only unstaged files
```

MILESTONE: Phase 1 Complete

---

## PHASE 2: HIGH-IMPACT CHANGES (P1)

**Goal**: Extract 3 Skills, compress examples, eliminate redundancy
**Time**: 4 hours
**Validation**: Startup context reduced by ~1,950 tokens

### TASK P1.1: Extract shell-enhancements Skill

STEP 1: Create directory
```bash
mkdir -p .claude/skills/shell-enhancements
```

STEP 2: Read source content
READ: `.claude/PROJECT.md` lines 321-413
COPY entire section starting with "## Shell Enhancements for LLM-Led Development"

STEP 3: Create Skill file
WRITE: `.claude/skills/shell-enhancements/SKILL.md`
CONTENT:
```markdown
# shell-enhancements

**Description**: WSL2 shell commands optimized for Claude Code workflows including context gathering (context, recent, todos), git shortcuts (gcom, gamend, gnew), and session management (save-context, diagnose). Includes 35+ commands with auto-detection for Python/Node/Rust/Go projects.

**Triggers**: WSL2, shell commands, bash, git workflow, session management, context gathering, gcom, gamend, recent, todos, save-context, diagnose, shell enhancements

**Token Cost**: ~900 tokens when loaded

**Dependencies**: WSL2 environment, bash, git, modern CLI tools (optional: fd, rg, bat)

---

[PASTE CONTENT FROM PROJECT.md LINES 321-413 HERE]
```

STEP 4: Replace in PROJECT.md
READ: `.claude/PROJECT.md` to find current line numbers (may have shifted)
FIND section: "## Shell Enhancements for LLM-Led Development"
REPLACE entire section (lines 321-413) with:
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

VALIDATE:
```bash
wc -l .claude/skills/shell-enhancements/SKILL.md  # Should be ~95-105 lines
grep -c "shell-enhancements" .claude/PROJECT.md  # Should be 2-3
./scripts/optimization/token-counter.sh | grep "PROJECT.md"  # Should show decrease
```

IF validation FAILS → STOP, report error

---

### TASK P1.2: Extract development-tools Skill

STEP 1: Create directory
```bash
mkdir -p .claude/skills/development-tools
```

STEP 2: Read source content
READ: `.claude/PROJECT.md` lines 72-116
COPY section: "### LLM-Optimized Tools (Installed)"

STEP 3: Create Skill file
WRITE: `.claude/skills/development-tools/SKILL.md`
CONTENT:
```markdown
# development-tools

**Description**: LLM-optimized development tools including tokei (code stats), ripgrep (fast search), fd (find files), bat (syntax highlighting), jq/yq (JSON/YAML parsing), hyperfine (benchmarking), and httpie (HTTP requests). Includes comparison table to traditional Unix tools.

**Triggers**: tokei, ripgrep, rg, fd, bat, jq, yq, hyperfine, httpie, code analysis, search code, find files, parse JSON, development tools

**Token Cost**: ~500 tokens when loaded

**Dependencies**: Modern CLI tools (installation optional, Skill provides fallback guidance)

---

[PASTE CONTENT FROM PROJECT.md LINES 72-116 HERE]
```

STEP 4: Replace in PROJECT.md
FIND section starting with: "### LLM-Optimized Tools (Installed)"
REPLACE entire section (lines 72-116) with:
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

VALIDATE:
```bash
wc -l .claude/skills/development-tools/SKILL.md  # Should be ~50-60 lines
grep -c "development-tools" .claude/PROJECT.md  # Should be 2-3
```

IF validation FAILS → STOP, report error

---

### TASK P1.3: Extract testing-guidelines Skill (Consolidate)

STEP 1: Create directory
```bash
mkdir -p .claude/skills/testing-guidelines
```

STEP 2: Read source content from MULTIPLE locations
READ:
- `CLAUDE.md` lines 125-153 (test patterns)
- `.claude/PROJECT.md` lines 206-231 (testing workflows)
- `.claude/PROJECT.md` lines 489-508 (duplicate testing patterns)

STEP 3: Create consolidated Skill
WRITE: `.claude/skills/testing-guidelines/SKILL.md`
CONTENT:
```markdown
# testing-guidelines

**Description**: Comprehensive pytest patterns for Obra including WSL2 resource limits (0.5s sleep, 5 threads, 20KB memory), shared fixtures (test_config, fast_time), threading patterns, and crash prevention. Includes detailed examples of mocking, cleanup, and integration testing.

**Triggers**: pytest, testing, test patterns, fixtures, fast_time, WSL2 crashes, thread safety, test_config, threading, test guidelines

**Token Cost**: ~600 tokens when loaded

**Dependencies**: pytest, test fixtures from conftest.py

---

## Critical Resource Limits (WSL2 Crash Prevention)

MUST follow these limits to prevent WSL2 kernel panics:

- **Max sleep**: 0.5s per test
- **Max threads**: 5 per test
- **Max memory**: 20KB per test allocation
- **Mandatory**: `timeout=` on all thread joins
- **Mark heavy tests**: `@pytest.mark.slow`

**Why**: M2 testing caused WSL2 crashes from 75s cumulative sleeps, 25+ threads, 100KB+ memory.

**Full Documentation**: `docs/testing/TEST_GUIDELINES.md`

---

## Shared Fixtures

ALWAYS use these fixtures from conftest.py:

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

MUST use timeouts on all joins:

```python
def test_concurrent(test_config):
    """Test concurrent operations."""
    threads = [Thread(target=worker) for _ in range(3)]  # Max 5
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)  # MANDATORY - prevents hangs
```

---

## Test Commands

```bash
pytest                           # All tests
pytest --cov=src --cov-report=term  # With coverage
pytest -m "not slow"             # Fast tests only
pytest tests/test_state.py       # Specific module
watchexec -e py pytest           # Auto-run on changes
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
```

---

## Critical Notes

- 88% unit test coverage missed 6 bugs
- MUST write integration tests
- NEVER skip thread cleanup → WSL2 crash
- NEVER exceed resource limits → WSL2 crash
```

STEP 4: Update CLAUDE.md
FIND section: "## Testing - CRITICAL Rules" (lines 125-153)
REPLACE entire section with:
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

STEP 5: Update PROJECT.md testing workflows section
FIND section: "### Testing Workflows" (lines 206-231)
REPLACE with:
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

STEP 6: DELETE duplicate section in PROJECT.md
FIND section: "### Testing Patterns" (lines 489-508)
DELETE entire section

VALIDATE:
```bash
wc -l .claude/skills/testing-guidelines/SKILL.md  # Should be ~100-130 lines
grep -c "testing-guidelines" CLAUDE.md  # Should be 2
grep -c "Testing Patterns" .claude/PROJECT.md  # Should be 0 (deleted)
```

IF validation FAILS → STOP, report error

---

### TASK P1.4: Compress Long Examples in CLAUDE.md

READ: `CLAUDE.md`

CHANGE 1: Lines ~139-153 (test patterns example)
FIND:
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

REPLACE with:
```python
# Use fixtures: test_config, fast_time
def test_with_config(test_config):
    orch = Orchestrator(config=test_config)

def test_concurrent():
    threads = [Thread(target=work) for _ in range(3)]  # Max 5
    [t.start() for t in threads]; [t.join(timeout=5.0) for t in threads]
```

---

CHANGE 2: Lines ~240-252 (data flow diagram)
FIND:
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

REPLACE with:
```
User → NL Processing → Orchestrator → StateManager → Task
          ↓
    PromptBuilder → Agent → Validation(3) → Decision → StateManager/Git

Details: .claude/PROJECT.md (Architecture section)
```

---

CHANGE 3: Lines ~280-295 (quick reference examples)
FIND:
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

REPLACE with:
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

VALIDATE:
```bash
./scripts/optimization/find-long-examples.sh | grep "CLAUDE.md"  # Should show 3 fewer violations
```

IF validation FAILS → STOP, report error

---

### PHASE 2 VALIDATION

RUN:
```bash
./scripts/optimization/token-counter.sh
./scripts/optimization/find-long-examples.sh
./scripts/optimization/validate-structure.sh
```

VERIFY:
- ✅ 3 Skills created (shell-enhancements, development-tools, testing-guidelines)
- ✅ PROJECT.md reduced by ~1,400 tokens
- ✅ CLAUDE.md reduced by ~150 tokens
- ✅ Long examples in CLAUDE.md reduced
- ✅ No duplicate testing content

IF ANY check FAILS → STOP, report error, provide details

---

### PHASE 2 COMMIT

EXECUTE:
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

VALIDATE:
```bash
git log -1 --oneline | grep "P1 high-impact"  # Must match
git status  # Should be clean
```

MILESTONE: Phase 2 Complete

---

## PHASE 3: EXPANSION & POLISH (P2)

**Goal**: Create remaining Skills, expand files, achieve 100% compliance
**Time**: 3 hours
**Validation**: 27/27 rules passing

### TASK P2.1: Create agile-workflow Skill

FOLLOW same pattern as P1 Skills:
1. Create directory: `mkdir -p .claude/skills/agile-workflow`
2. Extract from PROJECT.md lines 303-319
3. Create SKILL.md with metadata
4. Replace source with summary + Skill reference

METADATA:
```markdown
**Description**: Epic, Story, Milestone management commands for Agile/Scrum workflows including creation (epic create, story create, milestone create), listing, execution, and completion tracking. Supports hierarchical task organization.
**Triggers**: epic, story, milestone, agile, scrum, task hierarchy, backlog, sprint
**Token Cost**: ~200 tokens when loaded
**Dependencies**: Obra CLI, StateManager
```

VALIDATE:
```bash
ls .claude/skills/agile-workflow/SKILL.md  # Must exist
```

---

### TASK P2.2: Create interactive-commands Skill

CONSOLIDATE from:
- CLAUDE.md lines 196-211
- PROJECT.md lines 284-301

METADATA:
```markdown
**Description**: Interactive mode command reference including natural language defaults (no / prefix), system commands (/help, /status, /pause, /resume, /stop, /to-impl, /override-decision), and command injection points during execution.
**Triggers**: interactive mode, /help, /status, /pause, /to-impl, command injection, interactive, /commands
**Token Cost**: ~250 tokens when loaded
**Dependencies**: Interactive CLI mode (python -m src.cli interactive)
```

VALIDATE:
```bash
ls .claude/skills/interactive-commands/SKILL.md  # Must exist
```

---

### TASK P2.3: Compress Remaining Long Examples in PROJECT.md

USE: `./scripts/optimization/find-long-examples.sh` to identify targets

TARGET: Top 5 longest examples in PROJECT.md

FOR EACH example:
1. FIND using line numbers from script
2. IDENTIFY compression opportunities:
   - Remove boilerplate
   - Use compact syntax
   - Combine related lines
   - Use comments instead of prose
3. COMPRESS to ≤10 lines
4. VALIDATE readability

VALIDATE after all compressions:
```bash
./scripts/optimization/find-long-examples.sh | grep "PROJECT.md"  # Should show 5 fewer
```

---

### TASK P2.4: Expand CLAUDE.md to Target Range

CURRENT: ~1,734 tokens (after P1)
TARGET: 3,000-5,000 tokens
NEED: +1,200 tokens

ADD 5 new sections:

SECTION 1: Skills Architecture (insert after line ~22, after "Essential Context")
```markdown
## Skills Architecture (v2.0)

**Progressive Disclosure**: Skills load on-demand when Claude determines relevance.

### When Skills Load
- **ALWAYS**: Metadata (description, triggers) in startup context
- **ON-DEMAND**: Full content when user task matches triggers
- **NEVER**: Skills not relevant to current task

### How to Invoke Skills
- Natural language mentions trigger keywords (e.g., "shell commands" → shell-enhancements)
- Explicit reference: "See shell-enhancements Skill"
- Claude auto-loads based on task analysis

### Available Skills
- `shell-enhancements` - 35+ WSL2 commands for workflows
- `development-tools` - LLM-optimized CLI tools (tokei, rg, fd, bat, jq)
- `testing-guidelines` - Pytest patterns, WSL2 crash prevention
- `agile-workflow` - Epic/Story/Milestone commands
- `interactive-commands` - Interactive mode reference

**See**: `.claude/skills/README.md` for complete list
```

SECTION 2: Context Management (insert after Rule 7)
```markdown
## Context Management (ADR-018)

### Session Refresh Triggers
MUST start new session IF:
- Context >80% capacity (red zone monitoring)
- Task type changed significantly
- Previous task complete and new task unrelated
- Confusion signals detected (repeated clarifications)

### Context Zones
- **Green** (<60%): Normal operation
- **Yellow** (60-85%): Monitor usage, compact if needed
- **Red** (>85%): Trigger self-handoff or manual refresh

### Context Compaction
WHEN context >60% full:
- Remove outdated tool results
- Summarize completed subtasks
- NEVER remove active task context
- Use CompactionStrategy from ADR-018

### Monitoring
- Track token usage per task
- Log handoff events in production logger
- Alert on red zone entry
```

SECTION 3: Rewind & Checkpoints (insert after Context Management)
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
5. Continue or try alternative approach

### Checkpoint Best Practices
- Create checkpoints at logical boundaries
- Name descriptively (not "checkpoint1")
- Review checkpoint list before major changes
- Use for experiment/rollback workflows
```

SECTION 4: MCP Server Integration (insert after Rewind)
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
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "env": {"ALLOWED_DIRECTORIES": "/path/to/project"}
    }
  }
}
```

### Usage
- MCP tools available automatically when server configured
- Claude invokes when needed (PR creation, issue search, file ops)
- Results count toward context budget
- Typical token cost: 100-500 per MCP operation

### Common Servers
- `@modelcontextprotocol/server-github` - GitHub operations
- `@modelcontextprotocol/server-filesystem` - Safe file access
- `@modelcontextprotocol/server-postgres` - Database queries
- Custom servers via MCP protocol
```

SECTION 5: Subagent Delegation (insert after MCP)
```markdown
## Subagent Delegation

### When to Create Subagents
CREATE subagent IF:
- Specialized task domain (testing, docs, deployment)
- Different tool permissions needed (restricted access)
- Isolated context beneficial (avoid pollution)
- Parallel work possible (multiple PRs, test suites)

DO NOT create IF:
- Main orchestrator can handle
- Overhead exceeds benefit
- Context sharing critical

### Configuration Pattern
`.claude/agents/{name}/config.json`:
```json
{
  "name": "test-agent",
  "model": "claude-haiku-4-5-20250919",
  "system_prompt": ".claude/agents/test-agent/system.md",
  "tools": ["bash", "edit_file"],
  "context": ["tests/", ".claude/skills/testing/"]
}
```

### Best Practices
- Use cheaper models (Haiku) for routine tasks
- Restrict tools to minimum needed
- Provide focused context
- Coordinate via orchestrator
```

VALIDATE:
```bash
wc -w CLAUDE.md  # Should be ~2,250-2,300 words
./scripts/optimization/token-counter.sh | grep "CLAUDE.md"  # Should show ~2,900-3,100 tokens
```

---

### TASK P2.5: Expand RULES.md to Target Range

CURRENT: ~1,136 tokens
TARGET: 2,000-4,000 tokens
NEED: +864 tokens

ADD 3 sections to end of file:

SECTION 1: Advanced StateManager Patterns
```markdown
## Advanced StateManager Patterns

### Atomic Operations
```python
# CORRECT: Single transaction
with state.transaction():
    task = state.create_task(project_id=1, title="...")
    state.update_task(task_id=task.task_id, status=TaskStatus.IN_PROGRESS)

# WRONG: Multiple commits (race conditions)
task = state.create_task(...)  # commit 1
state.update_task(...)  # commit 2
```

### Bulk Operations
```python
# Efficient: Batch updates
tasks = state.get_tasks(project_id=1)
updates = [{'task_id': t.task_id, 'status': TaskStatus.COMPLETED} for t in tasks]
state.bulk_update_tasks(updates)

# Inefficient: Loop commits
for task in tasks:
    state.update_task(task.task_id, status=TaskStatus.COMPLETED)
```

### Query Optimization
```python
# CORRECT: Single query with filters
active_tasks = state.get_tasks(
    project_id=1,
    status=TaskStatus.IN_PROGRESS,
    order_by='created_at DESC'
)

# WRONG: Multiple queries
all_tasks = state.get_tasks(project_id=1)
active_tasks = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]
```
```

SECTION 2: Common Error Messages and Fixes
```markdown
## Common Errors Quick Fix

| Error | Cause | Fix |
|-------|-------|-----|
| `StateManager not initialized` | Used `Config()` not `Config.load()` | `config = Config.load('config.yaml')` |
| `Agent not found in registry` | Typo in config.agent.type | Check `@register_agent()` decorator name |
| `Session lock conflict` | Reused session across iterations | Fresh session per iteration |
| `WSL2 kernel panic` | Test resource limits exceeded | Follow TEST_GUIDELINES.md limits |
| `LLM connection timeout` | Network/Ollama down | `orchestrator.reconnect_llm()` |
| `Profile not found` | Profile doesn't exist | Validate: `if profile in ProfileManager.list_profiles()` |
| `AttributeError: 'NoneType'` | LLM unavailable | Check `orchestrator.check_llm_available()` first |
| `ValidationError: quality too low` | Response incomplete/malformed | Review prompt clarity, check agent logs |
| `ConfidenceScoreError: below threshold` | Uncertain response | Trigger breakpoint, get human input |
```

SECTION 3: Quick Debugging Checklist
```markdown
## Debug Checklist

### When Task Fails
- [ ] Check LLM connection: `orchestrator.check_llm_available()`
- [ ] Review logs: `tail -f ~/obra-runtime/logs/production.jsonl`
- [ ] Verify StateManager state: `state.get_task(task_id)`
- [ ] Check validation pipeline stages: ResponseValidator → QualityController → ConfidenceScorer
- [ ] Inspect agent output: Look for parse errors, incomplete responses
- [ ] Review prompt: Too vague? Missing context?

### When Tests Fail
- [ ] Resource limits OK? (0.5s sleep, 5 threads, 20KB)
- [ ] Fixtures loaded? (test_config, fast_time)
- [ ] Thread cleanup? (join with timeout)
- [ ] Integration vs unit? (88% unit coverage missed 6 bugs)
- [ ] Mocks realistic? (Match production behavior)
- [ ] Test isolation? (No shared state between tests)

### When LLM Connection Fails
- [ ] Ollama running? `curl http://10.0.75.1:11434/api/tags`
- [ ] Model loaded? Check Ollama logs
- [ ] Network route? `ping 10.0.75.1`
- [ ] Config correct? `config.get('llm.api_url')`
- [ ] Timeout adequate? Increase for large responses

### When Git Operations Fail
- [ ] Working directory clean? `git status`
- [ ] GitManager initialized? Check orchestrator setup
- [ ] Permissions OK? Write access to repo
- [ ] Branch exists? `git branch -a`
- [ ] Remote configured? `git remote -v`
```

VALIDATE:
```bash
wc -w .claude/RULES.md  # Should be ~1,550-1,600 words
./scripts/optimization/token-counter.sh | grep "RULES.md"  # Should show ~2,000-2,100 tokens
```

---

### PHASE 3 VALIDATION

RUN:
```bash
./scripts/optimization/token-counter.sh
./scripts/optimization/find-long-examples.sh
./scripts/optimization/find-soft-language.sh
./scripts/optimization/validate-structure.sh
```

VERIFY:
- ✅ CLAUDE.md: 2,900-3,100 tokens
- ✅ PROJECT.md: 5,500-6,500 tokens (after compressions)
- ✅ RULES.md: 2,000-2,100 tokens
- ✅ 7 Skills total
- ✅ Skills metadata: 350 tokens
- ✅ Total startup: 6,500-7,500 tokens
- ✅ No long examples (all ≤10 lines)
- ✅ No soft language
- ✅ 27/27 rules passing (100% compliance)

IF ANY check FAILS → STOP, report error with details

---

### PHASE 3 COMMIT

EXECUTE:
```bash
git add .claude/ CLAUDE.md
git commit -m "feat: P2 optimization complete - 100% rule compliance

- Create agile-workflow and interactive-commands Skills
- Compress remaining long examples in PROJECT.md (5 examples)
- Expand CLAUDE.md with Skills architecture, context management, Rewind, MCP, subagents (+1,200 tokens)
- Expand RULES.md with patterns, errors, debug checklist (+864 tokens)
- Achieve 27/27 rule compliance (100%)
- Total managed: ~9,800 tokens (6,900 startup + 2,900 on-demand)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

VALIDATE:
```bash
git log -1 --oneline | grep "P2 optimization complete"  # Must match
git log --oneline -3  # Should show P0, P1, P2 commits
git status  # Should be clean
```

MILESTONE: All Phases Complete

---

## FINAL VALIDATION & REPORTING

### Run Complete Validation
```bash
./scripts/optimization/validate-structure.sh > /tmp/final-validation.txt
./scripts/optimization/token-counter.sh > /tmp/final-tokens.txt
./scripts/optimization/find-long-examples.sh > /tmp/final-examples.txt
./scripts/optimization/find-soft-language.sh > /tmp/final-soft-lang.txt
```

### Compare Before/After
```bash
diff /tmp/baseline-tokens.txt /tmp/final-tokens.txt
```

### Report Results
PRINT summary:
```
=== OPTIMIZATION COMPLETE ===

PHASE 1 (P0): ✅ Critical fixes
- .gitignore: ✅ Selective
- Soft language: ✅ Removed
- Skills directory: ✅ Created

PHASE 2 (P1): ✅ High-impact changes
- Skills extracted: 3 (shell-enhancements, development-tools, testing-guidelines)
- Examples compressed: 3 in CLAUDE.md
- Redundancy eliminated: ✅ Testing patterns consolidated
- Token savings: ~1,950 from startup

PHASE 3 (P2): ✅ Expansion & polish
- Skills created: 2 more (agile-workflow, interactive-commands)
- CLAUDE.md expanded: +1,200 tokens
- RULES.md expanded: +864 tokens
- Examples compressed: 5 more in PROJECT.md
- Rule compliance: 27/27 (100%)

FINAL METRICS:
- Total startup: X,XXX tokens (target: <15,000) ✅
- Skills on-demand: X,XXX tokens
- Long examples: 0 ❌
- Soft language: 0 ✅
- Compliance: 100% ✅

COMMITS:
- P0: <commit sha>
- P1: <commit sha>
- P2: <commit sha>

All validation scripts passing. Implementation complete.
```

---

## ERROR HANDLING

IF error at ANY step:
1. STOP immediately
2. REPORT:
   - Phase and task where error occurred
   - Error message
   - Validation output
   - Current git status
3. DO NOT continue to next task
4. WAIT for user intervention

IF validation fails:
1. SHOW expected vs actual
2. SHOW script output
3. SUGGEST fix
4. WAIT for confirmation before retrying

IF line numbers shifted:
1. RE-READ file
2. SEARCH for content markers (section headers)
3. ADJUST line numbers
4. PROCEED with caution

---

## AUTONOMOUS EXECUTION NOTES

**Context awareness**:
- Line numbers WILL shift after edits
- ALWAYS re-read files before edits
- USE content markers (headers, unique strings) not just line numbers

**Validation discipline**:
- RUN validation after EVERY task
- DO NOT skip validation "to save time"
- Validation prevents cascading errors

**Commit hygiene**:
- ONE commit per phase
- DESCRIPTIVE commit messages
- ALWAYS include Co-Authored-By

**Token counting**:
- Words × 1.3 = approximate tokens
- USE scripts for accuracy
- CHECK before/after each change

**Skills extraction pattern**:
1. Create directory
2. Extract content
3. Create SKILL.md with metadata
4. Replace source with summary
5. Validate token reduction

**Example compression techniques**:
- Remove boilerplate
- Combine related lines
- Use list comprehensions
- Comments not prose
- Omit obvious parts

---

AUTONOMOUS EXECUTION PROTOCOL COMPLETE
READY FOR CLAUDE CODE LLM IMPLEMENTATION
