# Obra Documentation

**Obra** (Claude Code Orchestrator) - Intelligent supervision system for Claude Code with local LLM oversight.

## Quick Navigation

### 🚀 Getting Started
- **[Complete Setup Walkthrough](guides/COMPLETE_SETUP_WALKTHROUGH.md)** - Step-by-step setup for Windows 11 + Hyper-V + WSL2
- **[Getting Started Guide](guides/GETTING_STARTED.md)** - Quick start and basic usage
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

### 🛠️ Development
- **[Implementation Plan](development/IMPLEMENTATION_PLAN.md)** - Complete M0-M7 roadmap
- **[Test Guidelines](development/TEST_GUIDELINES.md)** - Critical testing best practices (prevent WSL2 crashes!)
- **[Milestone Summaries](development/milestones/)** - M1-M7 completion reports
- **[Status Report](development/STATUS_REPORT.md)** - Current project status
- **[WSL2 Postmortem](development/WSL2_TEST_CRASH_POSTMORTEM.md)** - Test crash analysis and fixes

### 📊 Business & Pitch
- **[Pitch Deck](business_dev/obra_pitch_deck.md)** - Obra value proposition
- **[Pitch Overview](business_dev/pitch_overview.md)** - Executive summary

### 📦 Archive
- **[Old Design Docs](archive/design/)** - Historical design documents
- **[Session Notes](archive/sessions/)** - Development session summaries

## Documentation Structure

```
docs/
├── guides/                     # User-facing guides
│   ├── COMPLETE_SETUP_WALKTHROUGH.md  (Windows 11 + Hyper-V + WSL2)
│   └── GETTING_STARTED.md              (Quick start)
├── architecture/               # System architecture
│   ├── ARCHITECTURE.md                 (Complete M0-M6 design)
│   ├── plugin_system.md
│   ├── data_flow.md
│   └── system_design.md
├── decisions/                  # Architecture Decision Records
│   ├── 001_why_plugins.md
│   ├── 002_deployment_models.md
│   ├── 003_state_management.md
│   └── ADR-003-file-watcher-thread-cleanup.md
├── development/                # Development documentation
│   ├── IMPLEMENTATION_PLAN.md          (M0-M7 roadmap)
│   ├── TEST_GUIDELINES.md              (Testing best practices)
│   ├── STATUS_REPORT.md
│   ├── WSL2_TEST_CRASH_POSTMORTEM.md
│   └── milestones/                     # M1-M7 completion summaries
│       ├── M1_PROGRESS.md
│       ├── M2_COMPLETION_SUMMARY.md
│       ├── M4_COMPLETION_SUMMARY.md
│       ├── M5_COMPLETION_SUMMARY.md
│       ├── M6_COMPLETION_SUMMARY.md
│       └── M7_COMPLETION_SUMMARY.md
├── business_dev/               # Business documentation
│   ├── obra_pitch_deck.md
│   └── pitch_overview.md
├── api/                        # API reference (future)
└── archive/                    # Historical documents
    ├── design/                 # Old design docs
    └── sessions/               # Development session notes
```

## Project Status

**Current Phase**: ✅ Production-ready (v1.0)

- **All M0-M7 milestones complete**
- **88% test coverage** (exceeds 85% target)
- **400+ comprehensive tests**
- **~15,000 lines of code** (production + tests + docs)
- **Docker deployment ready**
- **Comprehensive documentation**

## Next Steps

1. **Setup and test Obra** on actual Windows 11 + Hyper-V environment
2. **Real-world validation** with actual development tasks
3. **Performance tuning** based on usage metrics
4. **v1.1 features**: Web UI, pattern learning, multi-project orchestration

## Key Documents for Context Refresh

When starting a new session, read these documents to get up to speed:

1. **[Project README](../README.md)** - Overview and quick reference
2. **[CLAUDE.md](../CLAUDE.md)** - Project guidance for Claude Code
3. **[M7 Completion Summary](development/milestones/M7_COMPLETION_SUMMARY.md)** - Latest project status
4. **[Implementation Plan](development/IMPLEMENTATION_PLAN.md)** - Complete roadmap
5. **[System Architecture](architecture/ARCHITECTURE.md)** - Technical design

## Contributing

See [Project README](../README.md#contributing) for contribution guidelines.

## License

MIT License - See [LICENSE](../LICENSE) file for details.

---

**Built with ❤️ for autonomous software development**
