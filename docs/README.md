# Obra Documentation

**Obra** (Claude Code Orchestrator) - Intelligent supervision system for Claude Code with local LLM oversight.

## Quick Navigation

### 🚀 Getting Started
- **[Complete Setup Walkthrough](guides/COMPLETE_SETUP_WALKTHROUGH.md)** - Step-by-step setup for Windows 11 + Hyper-V + WSL2
- **[Getting Started Guide](guides/GETTING_STARTED.md)** - Quick start and basic usage
- **[Natural Language Command Guide](guides/NL_COMMAND_GUIDE.md)** - Conversational interaction with Obra (v1.3.0)
- **[Agile Workflow Guide](guides/AGILE_WORKFLOW_GUIDE.md)** - Epic/story/task workflows (v1.3.0)
- **[Project Infrastructure Guide](guides/PROJECT_INFRASTRUCTURE_GUIDE.md)** - Auto documentation maintenance (NEW - v1.4.0) 🆕
- **[Session Management Guide](guides/SESSION_MANAGEMENT_GUIDE.md)** - Per-iteration session architecture
- **[Agent Selection Guide](guides/AGENT_SELECTION_GUIDE.md)** - Choosing and configuring agents
- **[Migration Guide v1.3](guides/MIGRATION_GUIDE_V1.3.md)** - Upgrading from v1.2 to v1.3
- **[Configuration Profiles Guide](guides/CONFIGURATION_PROFILES_GUIDE.md)** - Pre-configured project profiles
- **[Prompt Engineering Guide](guides/PROMPT_ENGINEERING_GUIDE.md)** - LLM-First hybrid prompt framework

### 🏗️ Architecture
- **[System Architecture](architecture/ARCHITECTURE.md)** - Complete system design (v1.3.0 with NL Interface)
- **[Plugin System](architecture/plugin_system.md)** - Extensible agent/LLM framework
- **[Data Flow](architecture/data_flow.md)** - How data moves through the system
- **[System Design](architecture/system_design.md)** - High-level design decisions

### 📋 Architecture Decision Records (ADRs) - 15 Total
**Foundation ADRs (001-006)**:
- **[ADR-001: Why Plugins](decisions/001_why_plugins.md)** - Plugin system rationale
- **[ADR-002: Deployment Models](decisions/002_deployment_models.md)** - SSH/Docker/Local options
- **[ADR-003: State Management](decisions/003_state_management.md)** - StateManager as single source of truth
- **[ADR-003: File Watcher Cleanup](decisions/ADR-003-file-watcher-thread-cleanup.md)** - Thread safety fixes
- **[ADR-004: Local Agent Architecture](decisions/ADR-004-local-agent-architecture.md)** - Headless mode design
- **[ADR-005: Claude-Driven Parallelization](decisions/ADR-005-claude-driven-parallelization.md)** - Parallelization approach
- **[ADR-006: LLM-First Prompts](decisions/ADR-006-llm-first-prompts.md)** - Hybrid prompt format

**Feature ADRs (007-016)**:
- **[ADR-007-012: Various Features](decisions/)** - Session management, context, quality control, etc.
- **[ADR-013: Agile Work Hierarchy](decisions/ADR-013-adopt-agile-work-hierarchy.md)** - Epic/story/task model (v1.3.0)
- **[ADR-014: Natural Language Command Interface](decisions/ADR-014-natural-language-command-interface.md)** - Conversational commands (v1.3.0)
- **[ADR-015: Project Infrastructure Maintenance](decisions/ADR-015-project-infrastructure-maintenance-system.md)** - Auto documentation maintenance (v1.4.0) ✅
- **[ADR-016: Decompose NL Entity Extraction](decisions/ADR-016-decompose-nl-entity-extraction.md)** - NL pipeline refactor (v1.6.0 - Proposed) 🆕

### 🛠️ Development
**Active Development**:
- **[Test Guidelines](development/TEST_GUIDELINES.md)** - Critical testing best practices (prevent WSL2 crashes!)
- **[Database Migrations](development/DATABASE_MIGRATIONS.md)** - Database schema migration guide
- **[Real Orchestration Debug Plan](development/REAL_ORCHESTRATION_DEBUG_PLAN.md)** - Debugging reference
- **[WSL2 Postmortem](development/WSL2_TEST_CRASH_POSTMORTEM.md)** - Test crash analysis and fixes
- **[NL Command Interface Spec](development/NL_COMMAND_INTERFACE_SPEC.json)** - Machine-readable NL spec (v1.3.0)
- **[NL Command Test Specification](development/NL_COMMAND_TEST_SPECIFICATION.md)** - Comprehensive test plan (v1.3.0)
- **[ADR-016 Plans](development/)** - NL Pipeline Decomposition (v1.6.0 - Proposed) 🆕
  - `ADR016_SUMMARY.md` - Executive summary and quick overview
  - `ADR016_IMPLEMENTATION_PLAN.md` - Human-readable detailed plan
  - `ADR016_IMPLEMENTATION_PLAN.yaml` - Machine-optimized for LLM
  - `ADR016_EPIC_BREAKDOWN.md` - Story hierarchy and task breakdown
- **[Project Infrastructure Plans](development/)** - v1.4.0 implementation plans ✅
  - `PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.md` - Human-readable plan
  - `PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml` - Machine-optimized for LLM
  - `PROJECT_INFRASTRUCTURE_EPIC_BREAKDOWN.md` - Epic/story breakdown
  - Story summaries: `STORY_1.1_*`, `STORY_1.4_*`, `STORY_2.1_*`

### 📊 Quality Assurance
- **[Manual Testing Log](quality/MANUAL_TESTING_LOG.yaml)** - Issue tracking for pattern analysis (NEW) 🆕
- **[Issue Log Guide](quality/ISSUE_LOG_GUIDE.md)** - How to use the manual testing log
- **[Issue Analysis Tool](quality/analyze_issues.py)** - Generate statistics and insights

**Completed Plans** (Archived):
- See `archive/development/` for completed implementation plans:
  - NL_COMMAND_INTERFACE_IMPLEMENTATION_GUIDE.md
  - AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md
  - M9_IMPLEMENTATION_PLAN.md
  - INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md
  - FLEXIBLE_LLM_ORCHESTRATOR_IMPLEMENTATION_PLAN.md
  - HEADLESS_MODE_IMPLEMENTATION.md
  - CLAUDE_CODE_LOCAL_AGENT_PLAN.md
  - DYNAMIC_AGENT_LABELS_AND_MESSAGING_PLAN.md
  - And more...

### 🎨 Design
- **[System Overview](design/OBRA_SYSTEM_OVERVIEW.md)** - Comprehensive system overview (830+ lines)
- **[LLM-First Prompt Engineering Framework](design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md)** - Hybrid prompt design
- **[Future Design](design/design_future.md)** - Planned features and enhancements

### 📊 Business & Strategy
- **[Pitch Deck](business_dev/obra_pitch_deck.md)** - Obra value proposition
- **[Pitch Overview](business_dev/pitch_overview.md)** - Executive summary
- **[Flexible LLM Strategy](business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md)** - Dual deployment model (v1.3.0)

### 📦 Archive
- **[Archive Overview](archive/README.md)** - Complete archive documentation
- **[Archived Milestones](archive/milestones/)** - M1-M9 completion summaries
- **[Archived Implementation Plans](archive/development/)** - Completed plans (10+ docs)
- **[Archived Design Docs](archive/design/)** - Historical design documents

## Documentation Structure

```
docs/
├── guides/                            # User-facing guides (10 guides)
│   ├── COMPLETE_SETUP_WALKTHROUGH.md     (Windows 11 + Hyper-V + WSL2)
│   ├── GETTING_STARTED.md                (Quick start)
│   ├── NL_COMMAND_GUIDE.md               (Natural language commands - v1.3.0)
│   ├── AGILE_WORKFLOW_GUIDE.md           (Epic/story workflows - v1.3.0)
│   ├── PROJECT_INFRASTRUCTURE_GUIDE.md   (Auto doc maintenance - v1.4.0) 🆕
│   ├── SESSION_MANAGEMENT_GUIDE.md       (Session architecture)
│   ├── MIGRATION_GUIDE_V1.3.md           (v1.2 → v1.3 migration)
│   ├── CONFIGURATION_PROFILES_GUIDE.md   (Project profiles)
│   ├── PROMPT_ENGINEERING_GUIDE.md       (LLM-First hybrid prompts)
│   └── AGENT_SELECTION_GUIDE.md          (Agent configuration)
├── architecture/                      # System architecture (4 docs)
│   ├── ARCHITECTURE.md                   (Complete v1.4.0 design) ✨ Updated
│   ├── plugin_system.md                  (Plugin framework)
│   ├── data_flow.md                      (Data flow diagrams)
│   └── system_design.md                  (Design decisions)
├── decisions/                         # Architecture Decision Records (14 ADRs)
│   ├── 001_why_plugins.md
│   ├── 002_deployment_models.md
│   ├── 003_state_management.md
│   ├── ADR-003-file-watcher-thread-cleanup.md
│   ├── ADR-004-local-agent-architecture.md
│   ├── ADR-005-claude-driven-parallelization.md
│   ├── ADR-006-llm-first-prompts.md
│   ├── ADR-007 through ADR-012...
│   ├── ADR-013-adopt-agile-work-hierarchy.md     🆕 v1.3.0
│   └── ADR-014-natural-language-command-interface.md  🆕 v1.3.0
├── design/                            # Design documentation (3 docs)
│   ├── OBRA_SYSTEM_OVERVIEW.md           (Complete system overview)
│   ├── LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md
│   └── design_future.md                  (Future features)
├── development/                       # Active development docs
│   ├── TEST_GUIDELINES.md                ⚠️ Critical - Prevent WSL2 crashes
│   ├── DATABASE_MIGRATIONS.md
│   ├── REAL_ORCHESTRATION_DEBUG_PLAN.md
│   ├── WSL2_TEST_CRASH_POSTMORTEM.md
│   ├── NL_COMMAND_INTERFACE_SPEC.json    🆕 v1.3.0
│   ├── NL_COMMAND_TEST_SPECIFICATION.md  🆕 v1.3.0
│   └── phase-reports/                    (Phase completion summaries)
├── quality/                           # Quality assurance (NEW) 🆕
│   ├── README.md                         (Quality directory overview)
│   ├── MANUAL_TESTING_LOG.yaml           (Issue tracking log)
│   ├── ISSUE_LOG_GUIDE.md                (How to use the log)
│   ├── ISSUE_TEMPLATE.yaml               (Template for new issues)
│   └── analyze_issues.py                 (Analysis utility)
├── business_dev/                      # Business documentation (3 docs)
│   ├── obra_pitch_deck.md
│   ├── pitch_overview.md
│   └── FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md
└── archive/                           # Historical documents
    ├── README.md                         (Archive index)
    ├── milestones/                       (M1-M9 completion summaries)
    ├── development/                      (10+ completed implementation plans) ✨ Updated
    ├── design/                           (Old design docs)
    └── sessions/                         (Development session notes)
```

## Project Status

**Current Version**: ✅ **v1.3.0** - Natural Language Interface Complete

**Key Achievements**:
- **All M0-M9 milestones complete** ✅
- **Natural Language Command Interface** (5 stories complete) 🆕
- **Agile Work Hierarchy** (Epic/Story/Task/Subtask model) 🆕
- **Interactive Streaming Interface** (8 slash commands, 6 checkpoints)
- **Flexible LLM Orchestrator** (Ollama, OpenAI Codex support)
- **88% test coverage** (exceeds 85% target)
- **873+ comprehensive tests** (770 unit + 103 NL)
- **Comprehensive documentation** (14 ADRs, 9 guides)

**Features (v1.3.0)**:
- ✅ Natural language work item creation ("Create an epic for user auth")
- ✅ Conversational multi-turn interactions (10-turn context history)
- ✅ Epic/Story/Task/Subtask hierarchy with milestones
- ✅ Interactive command injection (/pause, /to-impl, /to-orch, etc.)
- ✅ Dynamic agent labels (supports any LLM/agent combination)
- ✅ Configuration profiles (python_project, web_app, ml_project, etc.)
- ✅ Git auto-integration with semantic commits
- ✅ Task dependency system with cycle detection
- ✅ Retry logic with exponential backoff

**Architecture**:
- **Plugin System**: Extensible agents (Claude Code, Aider) and LLMs (Ollama, OpenAI)
- **StateManager**: Single source of truth with atomic transactions
- **Per-Iteration Sessions**: Fresh Claude session per iteration (100% reliability)
- **Headless Mode**: Fully autonomous operation via `--dangerously-skip-permissions`
- **LLM-First Prompts**: 35% token efficiency, 23% faster responses

## Key Documents for Context Refresh

When starting a new session, read these documents to get up to speed:

1. **[CLAUDE.md](../CLAUDE.md)** - Project guidance for Claude Code (ESSENTIAL)
2. **[System Overview](design/OBRA_SYSTEM_OVERVIEW.md)** - Complete system understanding (830 lines)
3. **[CHANGELOG.md](../CHANGELOG.md)** - Recent changes and version history
4. **[System Architecture](architecture/ARCHITECTURE.md)** - Technical architecture (v1.3.0)
5. **[NL Command Guide](guides/NL_COMMAND_GUIDE.md)** - Natural language interaction (NEW)
6. **[Agile Workflow Guide](guides/AGILE_WORKFLOW_GUIDE.md)** - Epic/story workflows (NEW)

## Testing

**Test Coverage**: 88% (exceeds 85% target)

**Test Breakdown** (v1.3.0):
- **Unit Tests**: 770 tests (M0-M9, core components)
- **NL Command Tests**: 103 tests (IntentClassifier, EntityExtractor, CommandValidator, CommandExecutor, ResponseFormatter, Integration)
- **Integration Tests**: E2E workflows, multi-component tests
- **Total**: 873+ comprehensive tests

**Critical**: Always read [TEST_GUIDELINES.md](development/TEST_GUIDELINES.md) before writing tests to prevent WSL2 crashes!

## Next Steps (v1.4 Roadmap)

1. **Budget & Cost Controls** (P0) - Token budget tracking and limits
2. **Metrics & Reporting System** (P0) - Task success rates, confidence calibration
3. **Checkpoint System** (P0) - Save/restore orchestration state
4. **Multi-language NL Support** - Spanish, French, German for NL commands
5. **Voice Input** - Speech-to-text → NL processing
6. **Web UI Dashboard** - Real-time orchestration monitoring

## Contributing

See [Project README](../README.md#contributing) for contribution guidelines.

## License

MIT License - See [LICENSE](../LICENSE) file for details.

---

**Version**: v1.3.0 (2025-11-11)
**Test Coverage**: 88% (873+ tests)
**Lines of Code**: ~20,000 (production + tests + docs)
**Architecture Decision Records**: 14 ADRs
**User Guides**: 9 comprehensive guides

**Built with ❤️ for autonomous software development**
