# Claude Code Orchestrator - Implementation Plan

## Vision
An intelligent orchestration system where a local LLM (Qwen) supervises and optimizes interactions with Claude Code CLI, enabling semi-autonomous software development with human oversight at critical decision points.

## Architecture Summary
```
┌─────────────────────────────────────────┐
│  Local LLM (Qwen on RTX 5090)           │
│  • Validates agent's work               │
│  • Generates optimized prompts          │
│  • Scores confidence                    │
│  • Detects breakpoints                  │
│  • Maintains project state              │
└────────────┬────────────────────────────┘
             │ Plugin Interface
             ▼
┌─────────────────────────────────────────┐
│  Agent Plugin (Pluggable)               │
│  • ClaudeCodeSSHAgent (VM)              │
│  • ClaudeCodeDockerAgent (Container)    │
│  • AiderAgent (Alternative)             │
│  • CustomAgent (User-defined)           │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  File System & State                    │
│  • FileWatcher tracks changes           │
│  • StateManager persists everything     │
│  • Checkpoints enable rollback          │
└─────────────────────────────────────────┘
```

## Project Metadata

| Property | Value |
|----------|-------|
| **Estimated LOC** | ~2000 (down from 3500 with plugin simplification) |
| **Timeline** | 6-8 weeks (56-66 hours) |
| **Complexity** | Medium-High |
| **Language** | Python 3.10+ |
| **Target Platform** | Windows 11 + WSL2 (primary), Docker (for distribution) |
| **Hardware** | RTX 5090 32GB VRAM, 64GB RAM minimum |

## Critical Success Factors

1. ✅ **Plugin system** enables multiple agent backends without core changes
2. ✅ **StateManager** is single source of truth - all state goes through it
3. ✅ **Validation before quality control** - order matters for correctness
4. ✅ **File watching** tracks all agent changes for rollback capability
5. ✅ **Breakpoints** enable human oversight at critical decision points
6. ✅ **No cost tracking** - subscription-based, focus on quality not cost
7. ✅ **Thread-safe operations** - concurrent access properly locked

## Architectural Principles

### 1. Plugin Architecture
- **Why**: Extensibility, testability, community contributions
- **Cost**: +3 hours upfront, saves 15-20 hours later
- **Implementation**: Abstract base classes with decorator registration

### 2. Single Source of Truth
- **Component**: StateManager
- **Rule**: All components MUST use StateManager (no direct DB access)
- **Benefit**: Prevents inconsistencies, enables atomic operations

### 3. Separation of Concerns
- **Validation**: Checks completeness and format (ResponseValidator)
- **Quality Control**: Checks correctness and requirements (QualityController)
- **Order matters**: Validate BEFORE quality control

### 4. Fail-Safe Defaults
- **Breakpoints**: When uncertain, pause for human input
- **Confidence thresholds**: Conservative (prefer false positives)
- **State persistence**: Save frequently, checkpoint before risky operations

## Milestones Overview

| ID | Milestone | Duration | Status | Dependencies |
|----|-----------|----------|--------|--------------|
| M0 | Architecture Foundation | 8h | ✅ Complete | None |
| M1 | Core Infrastructure | 12h | ✅ Complete | M0 |
| M2 | LLM & Agent Interfaces | 10h | ✅ Complete | M0, M1 |
| M3 | File Monitoring | 6h | ✅ Complete | M1 |
| M4 | Orchestration Engine | 14h | ✅ Complete | M1, M2, M3 |
| M5 | Utility Services | 6h | 🔴 Not Started | M1, M2 |
| M6 | Integration & CLI | 10h | 🔴 Not Started | M1-M5 |
| M7 | Testing & Deployment | 8h | 🔴 Not Started | M1-M6 |

**Total Estimated Time**: 66 hours (~8 weeks part-time or 2 weeks full-time)

**Critical Path**: M0 → M1 → M2 → M4 → M6 → M7

---

## Milestone 0: Architecture Foundation
**Duration**: 8 hours | **Week**: 1 | **Priority**: Critical Path

### Goal
Establish plugin system, core abstractions, and architectural documentation that will guide all subsequent development.

### Deliverables
- **0.1**: Plugin interfaces (AgentPlugin, LLMPlugin abstract base classes)
- **0.2**: Plugin registry (registration, discovery, validation)
- **0.3**: Architecture documentation (design decisions, diagrams, ADRs)

### Success Criteria
- ✅ Can instantiate different agent types via configuration
- ✅ Plugin decorator works correctly
- ✅ New developer can understand architecture in 30 minutes
- ✅ All architectural decisions documented with rationale

### Why This Matters
This is the **foundation** of extensibility. Skipping or rushing this phase will require major refactoring later (15-20 hours of rework). The 8 hours invested here saves weeks of technical debt.

**Detailed Plan**: `plans/00_architecture_overview.json`

---

## Milestone 1: Core Infrastructure
**Duration**: 12 hours | **Week**: 1-2 | **Priority**: Critical Path

### Goal
Build the data layer and state management - the "spine" of the system that everything else depends on.

### Deliverables
- **1.1**: Database schema (SQLAlchemy models for all tables)
- **1.2**: StateManager (CRUD operations, transactions, checkpoints)
- **1.3**: Configuration management (YAML loader with validation)
- **1.4**: Exception hierarchy (typed exceptions with context)

### Success Criteria
- ✅ Can create projects and tasks with proper relationships
- ✅ Transactions rollback correctly on errors
- ✅ State snapshots are complete and restorable
- ✅ 95% test coverage on StateManager
- ✅ Configuration validates against schema

### Why This Matters
StateManager is the **single source of truth**. If this is buggy or slow, everything built on top will be unreliable. This is the most critical phase - quality over speed.

**Detailed Plan**: `plans/01_foundation.json`

---

## Milestone 2: LLM & Agent Interfaces
**Duration**: 10 hours | **Week**: 2-3 | **Priority**: Critical Path

### Goal
Connect to local LLM (Qwen) and implement agent plugins (Claude Code via SSH/Docker).

### Deliverables
- **2.1**: ✅ LocalLLMInterface (Ollama integration with streaming)
- **2.2**: ✅ ClaudeCodeSSHAgent (VM deployment via paramiko)
- **2.3**: ✅ OutputMonitor (watches agent stdout for completion)
- **2.4**: ✅ PromptGenerator (Jinja2 templates with context management)
- **2.5**: ✅ ResponseValidator (completeness and format validation)

### Success Criteria
- ✅ Can send prompts to local LLM and receive responses
- ✅ Can connect to Claude Code in VM via SSH
- ✅ Output monitor detects completion accurately
- ✅ Prompts fit within context windows
- ✅ Validation catches incomplete responses

### Why This Matters
This connects the **brain (local LLM)** to the **hands (agent)**. The plugin architecture implemented in M0 pays off here - we can swap agents without changing core logic.

**Detailed Plan**: `plans/02_interfaces.json`

---

## Milestone 3: File Monitoring
**Duration**: 6 hours | **Week**: 3 | **Priority**: Important

### Goal
Track what files the agent creates/modifies to enable validation and rollback.

### Deliverables
- **3.1**: FileWatcher (watchdog library for change detection)
- **3.2**: EventDetector (detects completion, failures, milestones)

### Success Criteria
- ✅ Detects all file changes within 1 second
- ✅ Filters correctly by pattern (ignores __pycache__, etc.)
- ✅ Debouncing prevents duplicate events
- ✅ Changes tracked in StateManager with hashes

### Why This Matters
Without file watching, we can't know what the agent actually did. This enables validation ("did it create the expected files?") and rollback ("restore to checkpoint").

**Detailed Plan**: `plans/03_monitoring.json`

---

## Milestone 4: Orchestration Engine
**Duration**: 14 hours | **Week**: 4-5 | **Priority**: Critical Path

### Goal
Implement the decision-making and task management logic - the "brain" of the system.

### Deliverables
- **4.1**: TaskScheduler (dependency resolution, priority queue)
- **4.2**: DecisionEngine (confidence-based routing, action selection)
- **4.3**: BreakpointManager (rule evaluation, resolution tracking)
- **4.4**: QualityController (multi-stage validation with gates)

### Success Criteria
- ✅ Tasks execute in correct order (dependencies respected)
- ✅ Breakpoints trigger at appropriate times
- ✅ Quality gates block low-quality outputs
- ✅ Can autonomously complete 70% of simple tasks
- ✅ Decision explanations are clear and accurate

### Why This Matters
This is where **intelligence** lives. Good decisions here mean fewer breakpoints and higher quality outputs. Poor decisions mean constant human intervention.

**Detailed Plan**: `plans/04_orchestration.json`

---

## Milestone 5: Utility Services
**Duration**: 6 hours | **Week**: 5 | **Priority**: Supporting

### Goal
Build supporting utilities for context management and confidence scoring.

### Deliverables
- **5.1**: TokenCounter (accurate counting for context management)
- **5.2**: ContextManager (prioritization, summarization)
- **5.3**: ConfidenceScorer (multi-factor scoring with calibration)

### Success Criteria
- ✅ Token counts accurate within 1%
- ✅ Context always fits within limits
- ✅ Confidence scores correlate with quality (>0.8 correlation)
- ✅ Summarization preserves key information

### Why This Matters
These utilities prevent **context overflow** and provide **accurate confidence** for decision making. Without them, prompts fail or decisions are unreliable.

**Detailed Plan**: `plans/05_utilities.json`

---

## Milestone 6: Integration & CLI
**Duration**: 10 hours | **Week**: 6 | **Priority**: Critical Path

### Goal
Integrate all components into main orchestration loop and provide user interface.

### Deliverables
- **6.1**: Orchestrator main loop (integrates all components)
- **6.2**: CLI interface (Click-based commands)
- **6.3**: Interactive mode (REPL for continuous interaction)

### Success Criteria
- ✅ Can run complete task end-to-end from CLI
- ✅ Main loop handles all scenarios (success, failure, breakpoints)
- ✅ State persists correctly across restarts
- ✅ Error recovery works gracefully
- ✅ CLI commands are intuitive and well-documented

### Why This Matters
This is where everything **comes together**. If phases 0-5 were done well, this phase should be straightforward. If not, problems will surface here.

**Detailed Plan**: `plans/06_integration.json`

---

## Milestone 7: Testing & Deployment
**Duration**: 8 hours | **Week**: 7-8 | **Priority**: Essential

### Goal
Achieve production-ready quality with comprehensive testing and easy deployment.

### Deliverables
- **7.1**: Unit tests (85% coverage overall, 90% critical modules)
- **7.2**: Integration tests (end-to-end workflows)
- **7.3**: Documentation (architecture, API reference, guides)
- **7.4**: Deployment automation (setup scripts, Docker Compose)

### Success Criteria
- ✅ All tests pass consistently
- ✅ Coverage targets met
- ✅ One-command setup works (`docker-compose up`)
- ✅ Documentation complete and accurate
- ✅ New user can get started in <10 minutes

### Why This Matters
This makes the system **shareable and maintainable**. Without proper tests and docs, the project dies when you step away from it.

**Detailed Plan**: `plans/07_deployment.json`

---

## Dependency Graph
```
M0 (Architecture)
 ├─→ M1 (Foundation)
 │    ├─→ M2 (Interfaces)
 │    │    └─→ M4 (Orchestration) ──→ M6 (Integration) ──→ M7 (Testing)
 │    ├─→ M3 (Monitoring) ─────────→ M4
 │    └─→ M5 (Utilities) ──────────→ M6
 └─→ M2
```

**Critical Path** (longest chain): M0 → M1 → M2 → M4 → M6 → M7 = 62 hours

**Parallel Opportunities**:
- M3 (Monitoring) can be done in parallel with M2 (Interfaces) if 2+ people
- M5 (Utilities) can be done in parallel with M4 (Orchestration)

---

## Progress Tracking

### Overall Progress: 38% Complete (3 of 8 milestones complete: M0, M1, M2)

| Milestone | Status | Progress | Started | Completed | Notes |
|-----------|--------|----------|---------|-----------|-------|
| M0: Architecture | 🟢 Complete | 3/3 deliverables | 2025-11-01 | 2025-11-01 | Plugin system, registry, and full documentation complete. Test coverage: 91% overall, 95.7% excluding ABCs |
| M1: Foundation | 🟢 Complete | 4/4 deliverables | 2025-11-01 | 2025-11-01 | StateManager, Config, Models, Exceptions complete with tests |
| M2: Interfaces | 🟢 Complete | 5/5 deliverables | 2025-11-01 | 2025-11-01 | All components complete: LocalLLMInterface, ClaudeCodeSSHAgent, OutputMonitor, PromptGenerator, ResponseValidator. 265 tests, comprehensive coverage |
| M3: Monitoring | 🔴 Not Started | 0/2 deliverables | - | - | |
| M4: Orchestration | 🔴 Not Started | 0/4 deliverables | - | - | |
| M5: Utilities | 🔴 Not Started | 0/3 deliverables | - | - | |
| M6: Integration | 🔴 Not Started | 0/3 deliverables | - | - | |
| M7: Testing | 🔴 Not Started | 0/4 deliverables | - | - | |

**Status Legend**:
- 🔴 Not Started
- 🟡 In Progress
- 🟢 Complete
- 🔵 Blocked
- ⚠️ At Risk

### Update Instructions

After completing each deliverable:
1. Update deliverable count (e.g., "1/4 deliverables")
2. Update progress percentage
3. Change status (🔴 → 🟡 → 🟢)
4. Add completion date
5. Note any issues or decisions in Notes column

Example after completing 0.1:
```markdown
| M0: Architecture | 🟡 In Progress | 1/3 deliverables | 2025-11-02 | - | Plugin interfaces done, moving to registry |
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|------------|--------|---------------------|-------|
| **SSH connection instability** | Medium | High | Implement reconnection logic with exponential backoff, health checks every 30s, keep-alive packets | M2 |
| **File watcher missing changes** | Low | High | Use proven library (watchdog), comprehensive test suite, debouncing logic | M3 |
| **State manager race conditions** | Medium | Critical | Thread-safe operations with proper locking, transaction tests, code review | M1 |
| **Agent process crashes** | High | Medium | Auto-restart with max retry limit, graceful degradation, checkpoint before risky operations | M2 |
| **Context window overflow** | Medium | Medium | Aggressive summarization, token counting, priority-based truncation | M5 |
| **Plugin interface too rigid** | Low | High | Start with minimal interface, iterate based on real implementations, version plugins | M0 |
| **Performance degradation** | Medium | Medium | Performance tests in M7, profiling, optimization pass, caching strategies | M7 |
| **Scope creep** | High | Medium | Strict adherence to milestone deliverables, defer features to v2.0, regular reviews | All |

### Risk Management Process
1. **Review risks** at start of each milestone
2. **Update likelihood/impact** based on learnings
3. **Document new risks** as they emerge
4. **Archive mitigated risks** with lessons learned

---

## Success Metrics

### Code Quality Targets

| Metric | Target | Measurement | Status |
|--------|--------|-------------|--------|
| Test Coverage (Overall) | ≥85% | pytest-cov | - |
| Test Coverage (Critical Modules) | ≥90% | StateManager, DecisionEngine, TaskScheduler | - |
| Linting Score | ≥9.0/10 | pylint | - |
| Type Coverage | ≥80% | mypy | - |
| Cyclomatic Complexity | ≤15 per function | radon | - |
| Documentation Coverage | 100% | All public APIs documented | - |

### Performance Targets

| Metric | Target | Measurement | Status |
|--------|--------|-------------|--------|
| Local LLM Response (p95) | <10s | Timer logs | - |
| Agent Interaction (p95) | <30s | End-to-end timing | - |
| State Operation (p95) | <100ms | Database query logs | - |
| Iteration Time (p95) | <60s | Full loop timing | - |
| Memory Usage (max) | <8GB | psutil monitoring | - |
| Startup Time | <30s | From launch to ready | - |
| File Change Detection | <1s | watchdog latency | - |

### Functionality Targets

| Metric | Target | Measurement | Status |
|--------|--------|-------------|--------|
| Autonomous Completion Rate | >70% | Tasks completed without breakpoints | - |
| False Breakpoint Rate | <5% | Unnecessary human interventions | - |
| Validation Accuracy | >90% | True positives / total validations | - |
| Confidence Correlation | >0.8 | Confidence score vs actual quality | - |
| Task Success Rate | >85% | Completed successfully / total tasks | - |
| Error Recovery Rate | >90% | Recovered / total errors | - |

### Measurement Process
- **Daily**: Log key metrics during development
- **Weekly**: Review metrics, identify trends
- **Per Milestone**: Formal measurement against targets
- **M7**: Comprehensive performance test suite

---

## Open Questions & Decisions

### Decisions Needed

- [ ] **M0**: Final plugin interface - do we need async support?
- [ ] **M1**: Database choice - SQLite for simplicity or PostgreSQL for robustness?
- [ ] **M2**: Primary agent implementation - SSH to VM or Docker first?
- [ ] **M5**: Context summarization - local LLM or rule-based?
- [ ] **M6**: CLI framework - Click or Typer?
- [ ] **M7**: Docker deployment priority - include in M7 or defer to later?

### Questions to Resolve

- [ ] How to handle Claude Code rate limits? (Auto-pause vs breakpoint)
- [ ] Should we support multiple agents in parallel? (v1.0 or v2.0?)
- [ ] Web UI priority? (Include in M7 or separate v1.1?)
- [ ] Pattern learning - when to start learning? (M4 or M7?)
- [ ] Checkpoint strategy - frequency and retention policy?

### Deferred to v2.0

- Multi-project orchestration (parallel projects)
- Real-time web dashboard
- Git integration (automatic commits)
- Multi-language support beyond Python
- Distributed execution across machines
- Advanced ML-based pattern learning
- Mobile app for breakpoint resolution

---

## Getting Started

### Prerequisites

1. **Hardware**:
   - NVIDIA GPU with 32GB VRAM (RTX 5090 or equivalent)
   - 64GB system RAM minimum
   - 100GB free disk space

2. **Software**:
   - Windows 11 Pro (for Hyper-V/WSL2)
   - Python 3.10 or higher
   - Ollama with Qwen2.5-Coder 32B model
   - Claude Code CLI (with subscription)
   - Docker Desktop (optional, for M7)
   - Git

3. **Accounts**:
   - Claude.ai subscription (for Claude Code)
   - GitHub account (for version control)

### Initial Setup
```bash
# 1. Clone repository (or create new one)
git clone <repo-url>
cd claude-code-orchestrator

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install development dependencies
pip install -r requirements-dev.txt

# 4. Verify Ollama is running
curl http://localhost:11434/api/tags

# 5. Verify Claude Code is accessible
wsl claude-code --version

# 6. Run validation script
python scripts/validate_env.py
```

### First Steps

1. **Read detailed plans**: Start with `plans/00_architecture_overview.json`
2. **Set up project structure**: Create directory tree as specified
3. **Begin M0**: Implement plugin interfaces
4. **Daily commits**: Commit after each deliverable
5. **Update this file**: Mark progress, add notes, document decisions

---

## Communication & Documentation

### Daily Updates
- Update progress table in this file
- Commit code with clear messages
- Note blockers or decisions needed

### Weekly Reviews
- Review metrics against targets
- Update risk register
- Adjust timeline if needed
- Document lessons learned

### Documentation Standards
- Code: Docstrings for all public APIs (Google style)
- Architecture: Keep docs/ folder up to date
- Decisions: Create ADR for major choices
- Changes: Update this plan if deviating

---

## Resources

### Documentation
- `docs/architecture/` - System design and diagrams
- `docs/decisions/` - Architecture Decision Records (ADRs)
- `docs/guides/` - How-to guides for developers
- `plans/` - Detailed phase-by-phase plans

### External References
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Click CLI](https://click.palletsprojects.com/)

### Tools
- **IDE**: VS Code with Python extension
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Linting**: pylint, black, isort
- **Type Checking**: mypy
- **Monitoring**: rich (progress bars), psutil (resource monitoring)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 2.0.0 | 2025-11-01 | Split into milestone-based structure, added plugin system | Initial |
| 1.0.0 | 2025-11-01 | Original monolithic plan | Initial |

---

## Notes

- This plan is a living document - update it as the project evolves
- When deviating from the plan, document why and update affected sections
- Celebrate milestones - they represent significant progress!
- Don't hesitate to adjust estimates based on actual experience

---

**Last Updated**: 2025-11-01  
**Next Review**: Start of M1  
**Plan Owner**: [Your Name]  
**Status**: Ready to Begin M0