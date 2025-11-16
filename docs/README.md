# Obra Documentation

**Obra** (Claude Code Orchestrator) - Intelligent supervision system for Claude Code with local LLM oversight.

## Quick Navigation

### ⭐ Start Here
- **[Product Overview](PRODUCT_OVERVIEW.md)** - ⭐ **NEW** - Comprehensive introduction to Obra (features, architecture, use cases)

### 🚀 Getting Started
- **[Complete Setup Walkthrough](guides/COMPLETE_SETUP_WALKTHROUGH.md)** - Step-by-step setup for Windows 11 + Hyper-V + WSL2
- **[Getting Started Guide](guides/GETTING_STARTED.md)** - Quick start and basic usage
- **[Natural Language Command Guide](guides/NL_COMMAND_GUIDE.md)** - Conversational interaction with Obra (v1.3.0)
- **[Agile Workflow Guide](guides/AGILE_WORKFLOW_GUIDE.md)** - Epic/story/task workflows (v1.3.0)
- **[Project Infrastructure Guide](guides/PROJECT_INFRASTRUCTURE_GUIDE.md)** - Auto documentation maintenance (v1.4.0)
- **[Session Management Guide](guides/SESSION_MANAGEMENT_GUIDE.md)** - Per-iteration session architecture
- **[Agent Selection Guide](guides/AGENT_SELECTION_GUIDE.md)** - Choosing and configuring agents
- **[Migration Guide v1.3](guides/MIGRATION_GUIDE_V1.3.md)** - Upgrading from v1.2 to v1.3
- **[Configuration Profiles Guide](guides/CONFIGURATION_PROFILES_GUIDE.md)** - Pre-configured project profiles
- **[Prompt Engineering Guide](guides/PROMPT_ENGINEERING_GUIDE.md)** - LLM-First hybrid prompt framework
- **[Interactive Streaming Quickref](guides/INTERACTIVE_STREAMING_QUICKREF.md)** - v1.5.0 interactive mode commands
- **[ADR-017 Migration Guide](guides/ADR017_MIGRATION_GUIDE.md)** - v1.7.0 API migration (internal)

### 🏗️ Architecture
- **[System Architecture](architecture/ARCHITECTURE.md)** - Complete system design (v1.3.0 with NL Interface)
- **[Plugin System](architecture/plugin_system.md)** - Extensible agent/LLM framework
- **[Data Flow](architecture/data_flow.md)** - How data moves through the system
- **[System Design](architecture/system_design.md)** - High-level design decisions

### 📋 Architecture Decision Records (ADRs) - 17 Total
**Foundation ADRs (001-006)**:
- **[ADR-001: Why Plugins](decisions/001_why_plugins.md)** - Plugin system rationale
- **[ADR-002: Deployment Models](decisions/002_deployment_models.md)** - SSH/Docker/Local options
- **[ADR-003: State Management](decisions/003_state_management.md)** - StateManager as single source of truth
- **[ADR-003: File Watcher Cleanup](decisions/ADR-003-file-watcher-thread-cleanup.md)** - Thread safety fixes
- **[ADR-004: Local Agent Architecture](decisions/ADR-004-local-agent-architecture.md)** - Headless mode design
- **[ADR-005: Claude-Driven Parallelization](decisions/ADR-005-claude-driven-parallelization.md)** - Parallelization approach
- **[ADR-006: LLM-First Prompts](decisions/ADR-006-llm-first-prompts.md)** - Hybrid prompt format

**Feature ADRs (007-017)**:
- **[ADR-007-012: Various Features](decisions/)** - Session management, context, quality control, etc.
- **[ADR-013: Agile Work Hierarchy](decisions/ADR-013-adopt-agile-work-hierarchy.md)** - Epic/story/task model (v1.3.0)
- **[ADR-014: Natural Language Command Interface](decisions/ADR-014-natural-language-command-interface.md)** - Conversational commands (v1.3.0)
- **[ADR-015: Project Infrastructure Maintenance](decisions/ADR-015-project-infrastructure-maintenance-system.md)** - Auto documentation maintenance (v1.4.0)
- **[ADR-016: Decompose NL Entity Extraction](decisions/ADR-016-decompose-nl-entity-extraction.md)** - NL pipeline refactor (v1.6.0)
- **[ADR-017: Unified Execution Architecture](decisions/ADR-017-unified-execution-architecture.md)** - All NL commands through orchestrator (v1.7.0)

### 🧪 Testing
- **[Test Guidelines](testing/TEST_GUIDELINES.md)** - ⚠️ CRITICAL: Prevents WSL2 crashes
- **[Real LLM Testing Guide](testing/REAL_LLM_TESTING_GUIDE.md)** - Testing with real LLM integration
- **[WSL2 Test Crash Postmortem](testing/postmortems/WSL2_TEST_CRASH_POSTMORTEM.md)** - M2 crash analysis and prevention
- **[Test Profiles Guide](guides/TEST_PROFILES_GUIDE.md)** - Pytest profile system

### ⚙️ Operations
- **[Database Migrations](operations/DATABASE_MIGRATIONS.md)** - Database schema migration procedures

### 📊 Quality Assurance
- **[Manual Testing Log](quality/MANUAL_TESTING_LOG.yaml)** - Issue tracking for pattern analysis
- **[Issue Log Guide](quality/ISSUE_LOG_GUIDE.md)** - How to use the manual testing log
- **[Issue Analysis Tool](quality/analyze_issues.py)** - Generate statistics and insights

### 🎨 Design
- **[Product Overview](PRODUCT_OVERVIEW.md)** - ⭐ Comprehensive product introduction (standalone)
- **[System Overview](design/OBRA_SYSTEM_OVERVIEW.md)** - Comprehensive system overview (830+ lines)
- **[LLM-First Prompt Engineering Framework](design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md)** - Hybrid prompt design
- **[Future Design](design/design_future.md)** - Planned features and enhancements

### 📊 Business & Strategy
- **[Pitch Deck](business_dev/obra_pitch_deck.md)** - Obra value proposition
- **[Pitch Overview](business_dev/pitch_overview.md)** - Executive summary
- **[Flexible LLM Strategy](business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md)** - Dual deployment model (v1.3.0)

### 📦 Archive
- **[Archive Overview](archive/README.md)** - Complete archive documentation
- **[Phase Reports](archive/phase-reports/)** - Historical development phase summaries (M1-M9, PHASE_3-7)
- **[Archived Milestones](archive/milestones/)** - M1-M9 completion summaries
- **[Archived Implementation Plans](archive/)** - Completed planning documents
  - **[ADR-016 NL Refactor](archive/adr016_nl_refactor/)** - v1.6.0 NL pipeline redesign
  - **[NL Command System](archive/nl_command_system/)** - v1.6.2-v1.7.1 NL completion
  - **[ADR-017 Story 0](archive/adr017_story0_implementation/)** - v1.7.0-v1.7.2 unified execution & testing
  - **[Project Infrastructure v1.4](archive/project_infrastructure_v1.4/)** - Auto doc maintenance
  - **[Agile Hierarchy v1.3](archive/agile_hierarchy_v1.3/)** - Epic/story implementation
  - **[Interactive UX v1.5](archive/interactive_ux_v1.5/)** - UX improvement plans
  - **[Integration Testing](archive/integration_testing/)** - Test infrastructure plans
  - **[Headless Mode M8](archive/headless_mode_m8/)** - Headless mode implementation
  - **[Test Profile System](archive/test_profile_system/)** - Pytest profiles implementation
  - **[Quick Wins Planning](archive/quick_wins_planning/)** - Quick win strategies
  - **[Historical Planning](archive/historical_misc/)** - Miscellaneous planning docs

## Documentation Structure

```
docs/
├── PRODUCT_OVERVIEW.md                   # ⭐ START HERE - Comprehensive product introduction
├── guides/                               # User-facing guides (12 guides)
│   ├── COMPLETE_SETUP_WALKTHROUGH.md       (Windows 11 + Hyper-V + WSL2)
│   ├── GETTING_STARTED.md                  (Quick start)
│   ├── NL_COMMAND_GUIDE.md                 (Natural language commands)
│   ├── AGILE_WORKFLOW_GUIDE.md             (Epic/story workflows)
│   ├── PROJECT_INFRASTRUCTURE_GUIDE.md     (Auto doc maintenance)
│   ├── SESSION_MANAGEMENT_GUIDE.md         (Per-iteration sessions)
│   ├── AGENT_SELECTION_GUIDE.md            (Agent configuration)
│   ├── CONFIGURATION_PROFILES_GUIDE.md     (Project profiles)
│   ├── PROMPT_ENGINEERING_GUIDE.md         (Hybrid prompts)
│   ├── INTERACTIVE_STREAMING_QUICKREF.md   (Interactive mode - v1.5.0)
│   ├── ADR017_MIGRATION_GUIDE.md           (API migration - v1.7.0)
│   └── TEST_PROFILES_GUIDE.md              (Pytest profiles)
│
├── architecture/                         # System architecture
│   ├── ARCHITECTURE.md                     (Complete system design)
│   ├── plugin_system.md                    (Plugin framework)
│   ├── data_flow.md                        (Data flow diagrams)
│   └── system_design.md                    (High-level design)
│
├── decisions/                            # Architecture Decision Records (17 ADRs)
│   ├── 001_why_plugins.md                  (Foundation)
│   ├── ADR-013-adopt-agile-work-hierarchy.md (v1.3.0)
│   ├── ADR-014-natural-language-command-interface.md (v1.3.0)
│   ├── ADR-015-project-infrastructure-maintenance-system.md (v1.4.0)
│   ├── ADR-016-decompose-nl-entity-extraction.md (v1.6.0)
│   ├── ADR-017-unified-execution-architecture.md (v1.7.0)
│   └── ... (11 more ADRs)
│
├── testing/                              # Testing documentation (new)
│   ├── TEST_GUIDELINES.md                  (⚠️ CRITICAL - WSL2 crash prevention)
│   ├── REAL_LLM_TESTING_GUIDE.md           (Real LLM integration testing)
│   └── postmortems/                        (Historical incident analysis)
│       └── WSL2_TEST_CRASH_POSTMORTEM.md   (M2 crash analysis)
│
├── operations/                           # Operational procedures (new)
│   └── DATABASE_MIGRATIONS.md              (Schema migration guide)
│
├── design/                               # Design documents
│   ├── OBRA_SYSTEM_OVERVIEW.md             (Complete system overview)
│   ├── LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md (Hybrid prompts)
│   └── design_future.md                    (Future enhancements)
│
├── quality/                              # Quality assurance
│   ├── MANUAL_TESTING_LOG.yaml             (Issue tracking)
│   ├── ISSUE_LOG_GUIDE.md                  (Usage guide)
│   └── analyze_issues.py                   (Analysis tool)
│
├── business_dev/                         # Business strategy
│   ├── obra_pitch_deck.md                  (Value proposition)
│   ├── pitch_overview.md                   (Executive summary)
│   └── FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md (Dual deployment)
│
├── archive/                              # Archived documentation
│   ├── README.md                           (Archive index)
│   ├── phase-reports/                      (Historical phase summaries)
│   ├── milestones/                         (M1-M9 completions)
│   ├── adr016_nl_refactor/                 (v1.6.0 planning)
│   ├── nl_command_system/                  (v1.6.2-v1.7.1 planning)
│   ├── adr017_story0_implementation/       (v1.7.0-v1.7.2 planning)
│   ├── project_infrastructure_v1.4/        (v1.4.0 planning)
│   ├── agile_hierarchy_v1.3/               (v1.3.0 planning)
│   ├── interactive_ux_v1.5/                (v1.5.0 planning)
│   ├── integration_testing/                (Test infrastructure)
│   ├── headless_mode_m8/                   (M8 planning)
│   ├── test_profile_system/                (Profile system)
│   ├── quick_wins_planning/                (Quick wins)
│   ├── code-review-historical/             (Code reviews)
│   ├── historical_misc/                    (Miscellaneous)
│   └── ... (more archives)
│
└── development/                          # Active development work
    └── (empty - ready for new planning documents)
```

## Version History

- **v1.7.2** (2025-11-13) - Testing Infrastructure Foundation (Story 0)
- **v1.7.1** (2025-11-13) - Observability & Enhanced Confirmation UI
- **v1.7.0** (2025-11-13) - Unified Execution Architecture (ADR-017)
- **v1.6.0** (2025-11-xx) - NL Pipeline Decomposition (ADR-016)
- **v1.5.0** (2025-11-xx) - Interactive UX Improvements
- **v1.4.0** (2025-11-xx) - Project Infrastructure Maintenance (ADR-015)
- **v1.3.0** (2025-11-xx) - Agile Hierarchy + NL Commands (ADR-013, ADR-014)
- **v1.2.0** (2025-11-xx) - LLM-First Prompt Engineering (PHASE_6)
- **v1.0.0** (2025-10-xx) - Initial Release (M0-M9)

## Contributing

When adding new documentation:
1. **Active planning** → Use `docs/development/` (currently empty)
2. **Completed planning** → Archive to appropriate `docs/archive/` subfolder
3. **Architecture decisions** → Use `docs/decisions/` (ADR format)
4. **User guides** → Use `docs/guides/`
5. **Testing docs** → Use `docs/testing/`
6. **Operations docs** → Use `docs/operations/`
7. **Design documents** → Use `docs/design/`

See [CLAUDE.md](../CLAUDE.md) for detailed contribution guidelines.

---

**Last Updated**: 2025-11-13
**Documentation Version**: v1.7.2
**Total Documents**: 100+ documents (active + archived)
**Archive Contents**: 46+ completed planning documents from v1.3.0-v1.7.2
