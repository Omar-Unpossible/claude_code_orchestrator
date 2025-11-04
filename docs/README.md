# Obra Documentation

**Obra** (Claude Code Orchestrator) - Intelligent supervision system for Claude Code with local LLM oversight.

## Quick Navigation

### 🚀 Getting Started
- **[Complete Setup Walkthrough](guides/COMPLETE_SETUP_WALKTHROUGH.md)** - Step-by-step setup for Windows 11 + Hyper-V + WSL2
- **[Getting Started Guide](guides/GETTING_STARTED.md)** - Quick start and basic usage
- **[Prompt Engineering Guide](guides/PROMPT_ENGINEERING_GUIDE.md)** - LLM-First hybrid prompt framework (NEW - PHASE_6)
- **[Agent Selection Guide](guides/AGENT_SELECTION_GUIDE.md)** - Choosing and configuring agents
- **[Project README](../README.md)** - Project overview and quick reference

### 🏗️ Architecture
- **[System Architecture](architecture/ARCHITECTURE.md)** - Complete system design (M0-M6)
- **[Plugin System](architecture/plugin_system.md)** - Extensible agent/LLM framework
- **[Data Flow](architecture/data_flow.md)** - How data moves through the system
- **[System Design](architecture/system_design.md)** - High-level design decisions

### 📋 Architecture Decision Records (ADRs)
- **[ADR-001: Why Plugins](decisions/001_why_plugins.md)** - Plugin system rationale
- **[ADR-002: Deployment Models](decisions/002_deployment_models.md)** - SSH/Docker/Local options
- **[ADR-003: State Management](decisions/003_state_management.md)** - StateManager as single source of truth
- **[ADR-003: File Watcher Cleanup](decisions/ADR-003-file-watcher-thread-cleanup.md)** - Thread safety fixes
- **[ADR-004: Local Agent Architecture](decisions/ADR-004-local-agent-architecture.md)** - Headless mode design
- **[ADR-005: Claude-Driven Parallelization](decisions/ADR-005-claude-driven-parallelization.md)** - Parallelization approach
- **[ADR-006: LLM-First Prompts](decisions/ADR-006-llm-first-prompts.md)** - Hybrid prompt format (NEW - PHASE_6)

### 🛠️ Development
- **[Implementation Plan](development/IMPLEMENTATION_PLAN.md)** - Complete M0-M7 roadmap
- **[LLM-First Implementation Plan](development/LLM_FIRST_IMPLEMENTATION_PLAN.yaml)** - PHASE-based plan (PHASE_6 complete)
- **[Test Guidelines](development/TEST_GUIDELINES.md)** - Critical testing best practices (prevent WSL2 crashes!)
- **[Database Migrations](development/DATABASE_MIGRATIONS.md)** - Database schema migration guide
- **[Claude Code Local Agent Plan](development/CLAUDE_CODE_LOCAL_AGENT_PLAN.md)** - M8 local agent design
- **[Real Orchestration Debug Plan](development/REAL_ORCHESTRATION_DEBUG_PLAN.md)** - Debugging reference (10 bugs fixed)
- **[WSL2 Postmortem](development/WSL2_TEST_CRASH_POSTMORTEM.md)** - Test crash analysis and fixes

### 🎨 Design
- **[LLM-First Prompt Engineering Framework](design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md)** - Hybrid prompt design
- **[Future Design](design/design_future.md)** - Planned features and enhancements

### 📊 Business & Pitch
- **[Pitch Deck](business_dev/obra_pitch_deck.md)** - Obra value proposition
- **[Pitch Overview](business_dev/pitch_overview.md)** - Executive summary

### 📦 Archive
- **[Archive Overview](archive/README.md)** - Complete archive documentation
- **[Archived Milestones](archive/milestones/)** - M1-M9 completion summaries (superseded)
- **[Archived Implementation Plans](archive/implementation-plans/)** - Completed plans
- **[Archived Development Docs](archive/development/)** - Outdated development documentation
- **[Archived Design Docs](archive/design/)** - Historical design documents
- **[Session Notes](archive/sessions/)** - Development session summaries

## Documentation Structure

```
docs/
├── guides/                     # User-facing guides
│   ├── COMPLETE_SETUP_WALKTHROUGH.md  (Windows 11 + Hyper-V + WSL2)
│   ├── GETTING_STARTED.md              (Quick start)
│   ├── PROMPT_ENGINEERING_GUIDE.md     (LLM-First hybrid prompts) ✨ NEW
│   └── AGENT_SELECTION_GUIDE.md        (Agent configuration)
├── architecture/               # System architecture
│   ├── ARCHITECTURE.md                 (Complete M0-M8 design)
│   ├── plugin_system.md
│   ├── data_flow.md
│   └── system_design.md
├── decisions/                  # Architecture Decision Records
│   ├── 001_why_plugins.md
│   ├── 002_deployment_models.md
│   ├── 003_state_management.md
│   ├── ADR-003-file-watcher-thread-cleanup.md
│   ├── ADR-004-local-agent-architecture.md
│   ├── ADR-005-claude-driven-parallelization.md
│   └── ADR-006-llm-first-prompts.md    ✨ NEW (PHASE_6)
├── design/                     # Design documentation
│   ├── LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md  ✨ (Current design)
│   └── design_future.md                           (Future planning)
├── development/                # Development documentation
│   ├── IMPLEMENTATION_PLAN.md                     (M0-M7 roadmap)
│   ├── LLM_FIRST_IMPLEMENTATION_PLAN.yaml         ✨ (PHASE_6 complete)
│   ├── TEST_GUIDELINES.md                         (Testing best practices)
│   ├── DATABASE_MIGRATIONS.md                     (Schema migrations)
│   ├── CLAUDE_CODE_LOCAL_AGENT_PLAN.md            (M8 local agent)
│   ├── REAL_ORCHESTRATION_DEBUG_PLAN.md           (Debugging reference)
│   ├── WSL2_TEST_CRASH_POSTMORTEM.md              (Testing issues)
│   └── milestones/                                (Milestone index only)
│       └── README.md
├── business_dev/               # Business documentation
│   ├── obra_pitch_deck.md
│   └── pitch_overview.md
├── api/                        # API reference (future)
└── archive/                    # Historical documents
    ├── README.md               ✨ (Archive documentation)
    ├── milestones/             (M1-M9 completion summaries)
    ├── implementation-plans/   (Completed plans)
    ├── development/            (Outdated dev docs)
    ├── design/                 (Old design docs)
    └── sessions/               (Development session notes)
```

## Project Status

**Current Phase**: ✅ Production-ready (v1.2) - LLM-First Framework Complete

- **All M0-M8 milestones complete** + **PHASE_6 (LLM-First) complete**
- **88% test coverage** (exceeds 85% target)
- **433+ comprehensive tests**
- **~17,800 lines of code** (production + tests + docs)
- **Docker deployment ready**
- **Comprehensive documentation**
- **✨ NEW: Hybrid prompt engineering** (35% token efficiency, 23% faster responses)

## Next Steps

1. **Setup and test Obra** on actual Windows 11 + Hyper-V environment
2. **Real-world validation** with actual development tasks
3. **Performance tuning** based on usage metrics
4. **v1.1 features**: Web UI, pattern learning, multi-project orchestration

## Key Documents for Context Refresh

When starting a new session, read these documents to get up to speed:

1. **[Project README](../README.md)** - Overview and quick reference
2. **[CLAUDE.md](../CLAUDE.md)** - Project guidance for Claude Code
3. **[PHASE_6 Completion Summary](/tmp/PHASE_6_COMPLETION_SUMMARY.md)** - Latest milestone (LLM-First framework)
4. **[M8 Completion Summary](archive/milestones/M8_COMPLETION_SUMMARY.md)** - Local agent implementation
5. **[LLM-First Implementation Plan](development/LLM_FIRST_IMPLEMENTATION_PLAN.yaml)** - Current roadmap (PHASE_6 complete)
6. **[System Architecture](architecture/ARCHITECTURE.md)** - Technical design

## Contributing

See [Project README](../README.md#contributing) for contribution guidelines.

## License

MIT License - See [LICENSE](../LICENSE) file for details.

---

**Built with ❤️ for autonomous software development**
