# Project Infrastructure Maintenance System v1.4.0 - Startup Prompt

**Use this prompt to kick off implementation in a fresh context window**

---

## 🚀 Startup Prompt (Copy & Paste This)

```
I need you to implement the Project Infrastructure Maintenance System (v1.4.0) for Obra. This feature automatically maintains project documentation (CHANGELOG, architecture docs, ADRs, guides) by creating maintenance tasks at key project events.

**Context Documents** (read in this order):
1. docs/decisions/ADR-015-project-infrastructure-maintenance-system.md - Architecture decision (WHY we're doing this)
2. docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml - Machine-optimized plan (WHAT to build)
3. docs/development/PROJECT_INFRASTRUCTURE_EPIC_BREAKDOWN.md - Story breakdown (HOW to organize work)
4. docs/development/TEST_GUIDELINES.md - Testing rules (MUST READ - prevents WSL2 crashes)
5. docs/guides/NL_COMMAND_GUIDE.md - Reference for natural language patterns

**Implementation Approach**:
- Follow the critical path: Story 1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2
- Start with Story 1.1: DocumentationManager Foundation
- Write tests as you go (TDD preferred)
- Check release gates before completing

**Story 1.1 Quick Start**:
1. Create `src/utils/documentation_manager.py`
2. Implement `DocumentationManager` class with 7 methods:
   - `__init__(state_manager, config)`
   - `check_documentation_freshness()` - detect stale docs
   - `create_maintenance_task()` - create Task with context
   - `generate_maintenance_prompt()` - build detailed prompt
   - `archive_completed_plans()` - move files to archive
   - `update_changelog()` - update CHANGELOG.md
   - `suggest_adr_creation()` - check if ADR needed
3. Write 20 unit tests (>90% coverage)

**Key Principles**:
- Event-driven: Hook into epic completion and milestone achievement
- Configuration-driven: Respect `documentation.enabled` config
- Context-rich: Maintenance tasks include epic details, changes, references
- Test-first: Write tests before implementation where possible
- Performance: Epic hook <500ms, milestone <1s

**Success Criteria** (v1.4.0 release gates):
- All 65 tests passing (57 unit + 8 integration)
- Test coverage >90% for new code
- Performance targets met
- Migration tested (forward and backward)
- Documentation complete

Let me know when you're ready to start, and I'll guide you through Story 1.1!
```

---

## Alternative: Concise Startup Prompt

```
Implement Project Infrastructure Maintenance System v1.4.0 for Obra.

**Read**:
1. docs/decisions/ADR-015-project-infrastructure-maintenance-system.md
2. docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml
3. docs/development/PROJECT_INFRASTRUCTURE_EPIC_BREAKDOWN.md

**Start**: Story 1.1 - Create `src/utils/documentation_manager.py` with 7 methods, 20 tests, >90% coverage.

**Goal**: Automatic documentation maintenance at epic/milestone completion. Epic hook <500ms, 65 tests passing.

Ready?
```

---

## What to Expect

When you paste this prompt into a fresh context:

1. **Claude will ask clarifying questions** (if needed)
2. **Claude will read the 3-5 referenced documents**
3. **Claude will start with Story 1.1**:
   - Create DocumentationManager skeleton
   - Implement methods one by one
   - Write tests incrementally
   - Verify >90% coverage
4. **Claude will move to Stories 1.2, 1.3, 1.4** sequentially
5. **Claude will complete Phase 1 (Week 1-2)**
6. **Claude will continue with Phase 2 (Week 3)**

---

## Tips for Success

### Do:
✅ Let Claude work autonomously - trust the plan
✅ Review code after each story completion
✅ Run tests frequently: `pytest tests/test_documentation_manager.py -v`
✅ Check performance: `pytest tests/integration/test_project_infrastructure.py::test_epic_completion_hook_performance`
✅ Ask Claude to explain if something is unclear

### Don't:
❌ Skip reading TEST_GUIDELINES.md (prevents WSL2 crashes!)
❌ Modify the critical path order (dependencies matter)
❌ Skip tests ("I'll write them later" never works)
❌ Rush through integration testing (Story 1.4 is critical)

---

## Monitoring Progress

### After Story 1.1 (Day 3):
```bash
# Check tests
pytest tests/test_documentation_manager.py -v --cov=src/utils/documentation_manager --cov-report=term-missing

# Expected:
# - 20 tests passing
# - >90% coverage for documentation_manager.py
```

### After Story 1.4 (Day 8):
```bash
# Check all tests
pytest tests/test_documentation_manager.py tests/integration/test_project_infrastructure.py -v

# Expected:
# - 53 tests passing (45 unit + 8 integration)
# - Phase 1 complete
```

### After Story 2.2 (Day 13):
```bash
# Final verification
pytest tests/test_documentation_manager.py tests/integration/test_project_infrastructure.py -v --cov=src/utils --cov-report=term-missing

# Expected:
# - 65 tests passing
# - >90% coverage
# - All release gates met
# - v1.4.0 ready for release
```

---

## Troubleshooting

**Problem**: Tests failing with "WSL2 crash"
**Solution**: Review `docs/development/TEST_GUIDELINES.md` - likely violating thread/sleep limits

**Problem**: Import errors for DocumentationManager
**Solution**: Check `src/utils/__init__.py` - may need to add import

**Problem**: Configuration not loading
**Solution**: Verify `config/default_config.yaml` has `documentation:` section

**Problem**: Performance tests failing (>500ms)
**Solution**: Check hook implementation - may need optimization or async processing

**Problem**: Migration fails
**Solution**: Check `migrations/versions/004_documentation_fields.sql` syntax

---

## Success Indicators

You'll know you're done when:

- ✅ All 65 tests passing
- ✅ Coverage report shows >90% for new code
- ✅ `obra epic execute <id>` creates maintenance task (if epic has flags)
- ✅ `obra milestone achieve <id>` creates comprehensive maintenance task
- ✅ CHANGELOG.md updated with v1.4.0 entry
- ✅ Documentation complete (guide + architecture updates)
- ✅ Manual QA: Epic completion workflow works end-to-end
- ✅ Manual QA: Milestone achievement workflow works end-to-end

---

**Ready to start? Copy the startup prompt above and paste into a fresh Claude Code session!** 🚀
