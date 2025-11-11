# Project Infrastructure Maintenance System - Epic & Story Breakdown

**Epic**: Project Infrastructure Maintenance System
**Target**: v1.4.0
**Priority**: P0 (High Priority)
**Est. Effort**: 15 days (3 weeks)

---

## Epic Summary

Automate project documentation maintenance by creating maintenance tasks at key project events (epic completion, milestone achievement) and periodic checks for stale documentation.

**Value**: Reduces manual overhead, ensures documentation stays fresh, enables Obra to "eat its own dog food" by maintaining its own project infrastructure.

---

## Story Hierarchy

```
Epic: Project Infrastructure Maintenance (v1.4.0)
├── Phase 1: Event-Driven Maintenance (Week 1-2)
│   ├── Story 1.1: DocumentationManager Foundation (3d) ⭐ CRITICAL PATH
│   ├── Story 1.2: StateManager Integration (2d) ⭐ CRITICAL PATH
│   ├── Story 1.3: Configuration System (1d) ⭐ CRITICAL PATH
│   └── Story 1.4: Integration Testing (2d) ⭐ CRITICAL PATH
└── Phase 2: Periodic Checks + Documentation (Week 3)
    ├── Story 2.1: Scheduled Freshness Checks (3d)
    └── Story 2.2: Documentation (2d)
```

**Total**: 6 stories, 13 implementation days (+ 2 days buffer)

---

## Story 1.1: DocumentationManager Foundation ⭐

**Priority**: P0 (Critical Path)
**Est**: 3 days
**Depends**: None

### User Story
```
As a developer,
I want Obra to detect when documentation is stale,
So that I know when documentation needs updating.
```

### Acceptance Criteria
- [ ] `DocumentationManager` class created in `src/utils/documentation_manager.py`
- [ ] `check_documentation_freshness()` identifies stale docs (>30/60/90 days)
- [ ] `create_maintenance_task()` creates Task with context
- [ ] `generate_maintenance_prompt()` builds detailed prompt
- [ ] `archive_completed_plans()` moves files to archive
- [ ] `update_changelog()` updates CHANGELOG.md
- [ ] `suggest_adr_creation()` detects if ADR needed
- [ ] 20 unit tests with >90% coverage

### Tasks
1. Create `src/utils/documentation_manager.py` skeleton
2. Implement `__init__(state_manager, config)`
3. Implement `check_documentation_freshness()`
4. Implement `create_maintenance_task()`
5. Implement `generate_maintenance_prompt()`
6. Implement `archive_completed_plans()`
7. Implement `update_changelog()`
8. Implement `suggest_adr_creation()`
9. Write 20 unit tests
10. Achieve >90% test coverage

---

## Story 1.2: StateManager Integration ⭐

**Priority**: P0 (Critical Path)
**Est**: 2 days
**Depends**: Story 1.1

### User Story
```
As Obra,
I want to automatically create documentation maintenance tasks when epics complete,
So that documentation stays up-to-date with code changes.
```

### Acceptance Criteria
- [ ] Task model has new fields: `requires_adr`, `has_architectural_changes`, `changes_summary`, `documentation_status`
- [ ] Milestone model has `version` field
- [ ] `StateManager.complete_epic()` creates maintenance task (if flags set)
- [ ] `StateManager.achieve_milestone()` creates comprehensive maintenance task
- [ ] Config `documentation.enabled: false` skips maintenance
- [ ] Migration `004_documentation_fields.sql` runs successfully
- [ ] 15 unit tests with >90% coverage

### Tasks
1. Add fields to Task model in `src/core/models.py`
2. Add field to Milestone model
3. Update `StateManager.complete_epic()` with hook
4. Update `StateManager.achieve_milestone()` with hook
5. Create migration `004_documentation_fields.sql`
6. Test migration forward/backward
7. Write 15 unit tests
8. Achieve >90% test coverage

---

## Story 1.3: Configuration System ⭐

**Priority**: P0 (Critical Path)
**Est**: 1 day
**Depends**: None

### User Story
```
As a user,
I want to configure documentation maintenance behavior,
So that I can enable/disable features and customize thresholds.
```

### Acceptance Criteria
- [ ] `documentation:` section added to `config/default_config.yaml`
- [ ] All settings documented with comments
- [ ] Configuration validation in `src/core/config.py`
- [ ] Invalid settings rejected with clear errors
- [ ] 10 config tests with 100% coverage

### Tasks
1. Add `documentation:` section to `default_config.yaml`
2. Add validation to `Config._validate_documentation_config()`
3. Write 10 configuration tests
4. Achieve 100% coverage for config loading

---

## Story 1.4: Integration Testing ⭐

**Priority**: P0 (Critical Path)
**Est**: 2 days
**Depends**: Stories 1.1, 1.2, 1.3

### User Story
```
As a developer,
I want end-to-end tests for the documentation maintenance workflow,
So that I know the entire pipeline works correctly.
```

### Acceptance Criteria
- [ ] 8 integration tests in `tests/integration/test_project_infrastructure.py`
- [ ] Epic complete → maintenance task flow works
- [ ] Milestone achieve → comprehensive maintenance works
- [ ] Configuration variations tested
- [ ] Performance targets met (epic <500ms, milestone <1s)

### Tasks
1. Create `tests/integration/test_project_infrastructure.py`
2. Write test: Epic complete → maintenance task
3. Write test: Milestone achieve → comprehensive
4. Write test: Config disabled skips maintenance
5. Write test: Config auto_maintain false notifies only
6. Write test: Maintenance task context complete
7. Write performance benchmarks
8. Verify all 8 tests pass

---

## Story 2.1: Scheduled Freshness Checks

**Priority**: P1
**Est**: 3 days
**Depends**: Stories 1.1, 1.2, 1.3, 1.4

### User Story
```
As a user,
I want Obra to periodically check for stale documentation,
So that I'm notified when docs need updating even if no epic completed.
```

### Acceptance Criteria
- [ ] `PeriodicScheduler` class added to DocumentationManager
- [ ] Weekly/monthly scans work correctly
- [ ] Stale docs detected (>30/60/90 days)
- [ ] Auto-create task if enabled
- [ ] Notification logged if auto-create disabled
- [ ] Graceful shutdown cancels timers
- [ ] 12 unit tests with >90% coverage

### Tasks
1. Add `PeriodicScheduler` class
2. Implement `schedule_periodic_check()`
3. Implement `cancel_scheduled_checks()`
4. Add notification logging
5. Add graceful shutdown hook
6. Write 12 unit tests
7. Test weekly/monthly scheduling
8. Test graceful shutdown

---

## Story 2.2: Documentation

**Priority**: P1
**Est**: 2 days
**Depends**: Story 2.1

### User Story
```
As a user,
I want comprehensive documentation for Project Infrastructure Maintenance,
So that I understand how to configure and use the feature.
```

### Acceptance Criteria
- [ ] User guide created: `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md` (~400 lines)
- [ ] Architecture doc updated with new component (~150 lines)
- [ ] CHANGELOG.md has v1.4.0 entry
- [ ] docs/README.md updated with links

### Tasks
1. Write `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md`
2. Update `docs/architecture/ARCHITECTURE.md`
3. Update `CHANGELOG.md` with v1.4.0
4. Update `docs/README.md`

---

## Test Summary

| Category | Count | Coverage Target |
|----------|-------|-----------------|
| Unit Tests (Story 1.1) | 20 | >90% |
| Unit Tests (Story 1.2) | 15 | >90% |
| Unit Tests (Story 1.3) | 10 | 100% |
| Integration Tests (Story 1.4) | 8 | N/A |
| Unit Tests (Story 2.1) | 12 | >90% |
| **Total** | **65** | **>90%** |

---

## Definition of Done (Epic-Level)

- [ ] All 6 stories complete (1.1-1.4, 2.1-2.2)
- [ ] 65 tests passing (57 unit + 8 integration)
- [ ] Test coverage >90% for all new code
- [ ] Performance targets met (epic hook <500ms, milestone <1s)
- [ ] Migration tested (forward and backward)
- [ ] Documentation complete (guide + architecture + CHANGELOG)
- [ ] Manual QA: Epic completion workflow
- [ ] Manual QA: Milestone achievement workflow
- [ ] Manual QA: Periodic check workflow
- [ ] Code review complete
- [ ] CHANGELOG.md updated
- [ ] Version tagged: v1.4.0

---

**References**:
- ADR-015: docs/decisions/ADR-015-project-infrastructure-maintenance-system.md
- Human Plan: docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.md
- Machine Plan: docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml
