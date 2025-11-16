# CLAUDE.md

Claude Code guidance for the Obra (Claude Code Orchestrator) project.

## Project Identity

**Obra** - AI orchestration platform combining local LLM reasoning (Qwen 2.5 Coder) with remote code generation (Claude Code CLI) for autonomous software development.

**Version**: v1.8.0 (Production Monitoring)
**Status**: Production-ready - 88% test coverage, validated performance
**Architecture**: Hybrid local-remote with multi-stage validation pipeline

## Essential Context on Session Start

Read in order:
1. **This file** - Core rules and principles
2. `.claude/PROJECT.md` - Commands, workflows, daily usage
3. `docs/design/OBRA_SYSTEM_OVERVIEW.md` - Complete system architecture
4. `CHANGELOG.md` - Recent changes
5. `docs/testing/TEST_GUIDELINES.md` - ⚠️ CRITICAL before writing tests

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

## Core Architecture Rules

### Rule 1: StateManager is Single Source of Truth
- **MUST**: All state access through StateManager
- **NEVER**: Direct database access
- **Why**: Prevents inconsistencies, enables atomic transactions, thread-safe
- **Pattern**: `orchestrator.state_manager.create_task()` not `db.session.add()`

### Rule 2: Validation Order is Fixed
**Sequence**: ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine

- **MUST**: Follow this exact order
- **NEVER**: Skip or reorder validation stages
- **Why**: Fast checks before expensive checks, different failure modes
- **Pattern**: Completeness before quality before confidence

### Rule 3: Plugin System for Extensibility
- **MUST**: Use `@register_agent()` and `@register_llm()` decorators
- **MUST**: Load from config, never hardcode implementations
- **Pattern**: `agent = AgentRegistry.get(config.get('agent.type'))()`

### Rule 4: Fresh Session Per Iteration
- **MUST**: New Claude Code session for each orchestration iteration
- **NEVER**: Reuse sessions across iterations
- **Why**: Eliminates session lock conflicts (PHASE_4 critical bug fix)
- **Implementation**: Uses `claude --print --dangerously-skip-permissions` via subprocess

### Rule 5: Hybrid Prompts (LLM-First)
- **JSON metadata**: Structured data (task context, constraints)
- **Natural language**: Instructions (what Claude does best)
- **Validated**: 35% token efficiency, 22% faster, 100% parse success
- **See**: `docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md`

### Rule 6: No Cost Tracking
- **Context**: Claude Code subscription (flat fee), not API billing
- **Track tokens**: For context management ONLY
- **Focus**: Quality over cost optimization

### Rule 7: Fail-Safe Defaults
- **When uncertain**: Trigger breakpoint (human input)
- **Conservative**: Prefer false positives on confidence
- **Checkpoint**: Before risky operations
- **Auto-save**: State saved frequently

## Key Components Quick Reference

### Architecture Layers
```
User Input → NL Processing → Orchestrator → StateManager
                ↓
Agent (Claude Code) ← StructuredPromptBuilder
                ↓
ResponseValidator → QualityController → ConfidenceScorer
                ↓
DecisionEngine → StateManager → GitManager (optional)
```

### Critical Classes
- **StateManager** (`src/core/state_manager.py`) - All state operations
- **Orchestrator** (`src/core/orchestrator.py`) - Main orchestration logic
- **DecisionEngine** (`src/core/decision_engine.py`) - Iteration control
- **StructuredPromptBuilder** (`src/prompts/`) - Hybrid prompt generation
- **AgentPlugin/LLMPlugin** (`src/plugins/`) - Extensibility interfaces

### Task Hierarchy (Agile/Scrum - ADR-013)
```
Product (Project)
  ↓ Epic (3-15 sessions, large feature)
    ↓ Story (1 session, user deliverable)
      ↓ Task (technical work, default)
        ↓ Subtask (via parent_task_id)

Milestone → Checkpoint (achievement marker)
```

## Code Standards

### Type Hints (Required)
```python
def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    """Google-style docstring with Args, Returns, Raises."""
    pass
```

### Exception Handling (Required)
```python
raise AgentException(
    "Cannot connect to agent",
    context={'host': host, 'port': port},
    recovery="Check network connectivity"
)
```

### Configuration-Driven (Required)
```python
# CORRECT: Load from config
config = Config.load('config.yaml')
agent = AgentRegistry.get(config.get('agent.type'))()

# WRONG: Hardcoded
agent = ClaudeCodeAgent()  # Don't do this
```

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

## Common Pitfalls (DO NOT DO)

### State Management
- ❌ Bypass StateManager for "quick reads"
- ❌ Direct database access (`db.session.add()`)
- ❌ Forget thread safety (use locks)

### Validation
- ❌ Reverse validation order (always Response → Quality → Confidence)
- ❌ Skip validation stages

### Configuration
- ❌ Use `Config()` directly (use `Config.load()`)
- ❌ Hardcode agents/LLMs (use plugin registry)
- ❌ Assume profile exists (validate first)
- ❌ Run setup.sh without `OBRA_RUNTIME_DIR` env var

### Testing
- ❌ Skip TEST_GUIDELINES.md (causes WSL2 crashes)
- ❌ Exceed resource limits (0.5s sleep, 5 threads, 20KB)
- ❌ Assume unit tests catch integration bugs (88% coverage missed 6 bugs)

### Session Management
- ❌ Reuse sessions across iterations (causes locks)
- ❌ Aggregate metrics at session level (use task-level)

### Model Attributes
- ❌ Use `project.name` (correct: `project.project_name`)
- ❌ Use `project.working_dir` (correct: `project.working_directory`)
- ✅ Check method signatures, use named arguments

### Documentation
- ❌ Save docs to project root or `/tmp`
- ✅ Use `docs/` subfolders: `development/`, `architecture/`, `decisions/`, `guides/`, `testing/`

### LLM Management
- ✅ Obra loads gracefully without LLM (allows later connection)
- ✅ Use `orchestrator.reconnect_llm()` to connect after startup
- ✅ Check `orchestrator.check_llm_available()` before executing tasks
- ❌ Don't panic if LLM unavailable (reconnect when ready)

## Interactive Mode (v1.5.0 UX)

**Natural text** (no `/`) defaults to orchestrator.
**System commands** require `/` prefix.

**See Skill**: `interactive-commands` for complete reference

**Key Commands**: `/help`, `/status`, `/pause`, `/resume`, `/to-impl <msg>`

## Natural Language Interface (v1.3.0 - ADR-014)

All NL commands route through orchestrator (Unified Execution - ADR-017):
- **IntentClassifier** → COMMAND vs QUESTION (95% accuracy)
- **EntityExtractor** → Schema-aware extraction (90% accuracy)
- **CommandValidator** → Business rules before execution
- **Pipeline**: NLCommandProcessor → Orchestrator → Validation

**Performance**: <3s P95 latency, validated in production

## Production Monitoring (v1.8.0)

**JSON Lines Format**: `~/obra-runtime/logs/production.jsonl`

**Key Events**:
- `user_input` - All user commands/NL text
- `nl_result` - Parsing quality metrics
- `execution_result` - Task outcomes
- `error` - Failures with context

**Privacy**: Auto-redacts PII (email, IP, phone) and secrets (API keys, tokens)
**Config**: `monitoring.production_logging.enabled` (default: true)

**See**: `docs/guides/PRODUCTION_MONITORING_GUIDE.md`

## Data Flow (Simplified)

```
User → NL Processing → Orchestrator → StateManager → Task
          ↓
    PromptBuilder → Agent → Validation(3) → Decision → StateManager/Git

Details: .claude/PROJECT.md (Architecture section)
```

**Interactive Checkpoints**: 6 injection points for user commands
**See**: `docs/architecture/data_flow.md` for detailed diagrams

## Environment & Deployment

**Target**: Windows 11 + Hyper-V → VM (WSL2 Ubuntu)
**LLM**: Qwen 2.5 Coder 32B via Ollama on RTX 5090 (host)
**Agent**: Claude Code CLI (WSL2 subprocess)
**Database**: SQLite (dev) or PostgreSQL (prod)
**Network**: LLM at `http://10.0.75.1:11434`

**See**: `docs/guides/COMPLETE_SETUP_WALKTHROUGH.md`

## Changelog Maintenance

**Update CHANGELOG.md** for:
- Features, bug fixes, architectural changes
- Performance improvements, breaking changes
- Format: Semantic versioning (MAJOR.MINOR.PATCH)
- Add under `[Unreleased]` section before committing

## Quick Reference - Daily Commands

**See `.claude/PROJECT.md`** for complete command listings.

Essential patterns:
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

## When Stuck - Documentation Map

**System Understanding**:
- `docs/design/OBRA_SYSTEM_OVERVIEW.md` - Complete architecture
- `docs/architecture/ARCHITECTURE.md` - Technical details
- `docs/decisions/` - 17 ADRs (architecture decisions)

**Guides** (in `docs/guides/`):
- `NL_COMMAND_GUIDE.md` - Natural language interface
- `AGILE_WORKFLOW_GUIDE.md` - Epic/story/milestone workflows
- `PROJECT_INFRASTRUCTURE_GUIDE.md` - Auto-doc maintenance
- `CONFIGURATION_PROFILES_GUIDE.md` - Profile setup
- `SESSION_MANAGEMENT_GUIDE.md` - Session handling
- `PRODUCTION_MONITORING_GUIDE.md` - Observability
- `INTERACTIVE_STREAMING_QUICKREF.md` - Interactive commands

**Testing**:
- `docs/testing/TEST_GUIDELINES.md` - ⚠️ Critical resource limits
- `docs/testing/postmortems/WSL2_TEST_CRASH_POSTMORTEM.md` - Why limits exist

**Historical Context**:
- `CHANGELOG.md` - Version history
- `docs/archive/` - Phase reports and analysis

## External References

- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Claude Code Docs](https://docs.claude.com/en/docs/claude-code)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Click CLI](https://click.palletsprojects.com/)
- [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)

## Version Info

**Last Updated**: November 15, 2025
**Current Version**: v1.8.0 (Production Monitoring)
**Test Coverage**: 88% (830+ tests)
**ADRs**: 17 architecture decision records
**Repository**: `git@github.com:Omar-Unpossible/claude_code_orchestrator.git`
