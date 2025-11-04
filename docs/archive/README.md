# Documentation Archive

This folder contains archived documentation that has been superseded, completed, or is no longer actively maintained.

**Archive Date**: 2025-11-03
**Archived As Part Of**: PHASE_6 completion and documentation reorganization

---

## Archive Organization

### `/milestones/`
**Old milestone completion summaries (M1-M9)**

These milestones have been superseded by the PHASE-based implementation approach (LLM-First Prompt Engineering Framework). The project has evolved from the original M0-M9 milestone structure to a more focused PHASE-based approach.

**Archived Files**:
- `M1_PROGRESS.md` - Early M1 progress (superseded by M1_COMPLETION_SUMMARY.md)
- `M2_COMPLETION_SUMMARY.md` - M2 LLM & Agent Interfaces completion
- `M4_PROGRESS.md` - Early M4 progress (superseded by M4_COMPLETION_SUMMARY.md)
- `M4_COMPLETION_SUMMARY.md` - M4 Orchestration Engine completion
- `M5_COMPLETION_SUMMARY.md` - M5 Utility Services completion
- `M6_COMPLETION_SUMMARY.md` - M6 Integration & CLI completion
- `M7_COMPLETION_SUMMARY.md` - M7 Testing & Deployment completion
- `M8_COMPLETION_SUMMARY.md` - M8 Local Agent Implementation completion
- `M9_COMPLETION_SUMMARY.md` - M9 Parameter Optimization completion
- `CLEANUP_V1_SUMMARY.md` - Early cleanup effort summary
- `HEADLESS_MODE_COMPLETION_SUMMARY.md` - Headless mode implementation (now part of M8)
- `POST_CLEANUP_VALIDATION.md` - Post-cleanup validation results

**Why Archived**: These milestones have been completed and their work has been integrated into the main codebase. The current focus is on PHASE-based development (LLM-First framework).

---

### `/implementation-plans/`
**Completed implementation plans**

These plans have been fully implemented and are no longer active development guides.

**Archived Files**:
- `M9_IMPLEMENTATION_PLAN.md` - M9 Parameter Optimization plan (completed)
- `PARAMETER_OPTIMIZATION_IMPLEMENTATION_PLAN.md` - Parameter optimization detailed plan (completed)

**Why Archived**: These implementation plans have been fully executed. Current active plan is `docs/development/LLM_FIRST_IMPLEMENTATION_PLAN.yaml`.

---

### `/development/`
**Outdated development documentation**

Development planning documents, status reports, and test plans that are no longer current.

**Archived Files**:
- `STATUS_REPORT.md` - Old project status (superseded by current README.md)
- `READINESS_SUMMARY.md` - Old readiness assessment (superseded)
- `REAL_ORCHESTRATION_READINESS_PLAN.md` - Orchestration readiness plan (completed)
- `REAL_WORLD_TEST_PLAN.md` - Real-world testing plan (completed)
- `VALIDATION_CHECKLIST.md` - Validation checklist (completed)
- `SIMPLIFIED_QUICK_START.md` - Old quick start (superseded by root QUICK_START.md)
- `QUICK_START_TESTING.md` - Quick start testing plan (completed)
- `TESTING_PACKAGE_SUMMARY.md` - Testing package summary (completed)
- `CLEANUP_PLAN_V2.md` - V2 cleanup plan (completed)
- `PRINT_MODE_ANALYSIS.md` - Print mode analysis (completed, now part of M8)
- `AUTHENTICATION_MODEL.md` - Authentication model design (not implemented)
- `COMPLEX_TASK_IDEAS.md` - Task ideas (not implemented)

**Why Archived**: These documents were part of development planning and testing phases that have been completed. Current active development docs are in `docs/development/`.

---

### `/design/`
**Superseded technical design documents**

Old technical design documents that have been replaced by more comprehensive architecture documentation.

**Archived Files**:
- `obra-technical-design.md` - Original technical design
- `obra-technical-design-enhanced.md` - Enhanced technical design

**Why Archived**: These early design documents have been superseded by the comprehensive architecture documentation in `docs/architecture/ARCHITECTURE.md` and the LLM-First framework design in `docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md`.

---

## Current Active Documentation

For current, active documentation, see:

### Architecture
- `docs/architecture/ARCHITECTURE.md` - Complete M0-M8 system architecture
- `docs/architecture/plugin_system.md` - Plugin system design
- `docs/architecture/data_flow.md` - Data flow diagrams

### Development
- `docs/development/IMPLEMENTATION_PLAN.md` - M0-M7 main implementation plan
- `docs/development/LLM_FIRST_IMPLEMENTATION_PLAN.yaml` - Current PHASE-based plan (PHASE_6 complete)
- `docs/development/TEST_GUIDELINES.md` - Critical testing guidelines
- `docs/development/DATABASE_MIGRATIONS.md` - Database migration guide
- `docs/development/CLAUDE_CODE_LOCAL_AGENT_PLAN.md` - M8 local agent plan
- `docs/development/REAL_ORCHESTRATION_DEBUG_PLAN.md` - Debugging reference
- `docs/development/WSL2_TEST_CRASH_POSTMORTEM.md` - WSL2 testing issues reference

### Guides
- `docs/guides/GETTING_STARTED.md` - Quick start guide
- `docs/guides/COMPLETE_SETUP_WALKTHROUGH.md` - Windows 11 + Hyper-V setup
- `docs/guides/PROMPT_ENGINEERING_GUIDE.md` - LLM-First prompt engineering guide
- `docs/guides/AGENT_SELECTION_GUIDE.md` - Agent selection and configuration

### Design
- `docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md` - Current framework design
- `docs/design/design_future.md` - Future planning

### Decisions
- `docs/decisions/ADR-003-file-watcher-thread-cleanup.md` - File watcher cleanup
- `docs/decisions/ADR-004-local-agent-architecture.md` - Local agent design
- `docs/decisions/ADR-005-claude-driven-parallelization.md` - Parallelization approach
- `docs/decisions/ADR-006-llm-first-prompts.md` - Hybrid prompt format decision

---

## How to Access Archived Content

All archived files are preserved in this folder for historical reference. If you need to reference old implementation details or design decisions, the files remain accessible here.

To view archived milestones:
```bash
ls docs/archive/milestones/
```

To view archived implementation plans:
```bash
ls docs/archive/implementation-plans/
```

---

**Last Updated**: 2025-11-03
**Archived By**: Documentation cleanup following PHASE_6 completion
