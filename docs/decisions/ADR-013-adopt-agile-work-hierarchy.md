# ADR-013: Adopt Agile/Scrum Work Hierarchy

**Date**: 2025-11-05
**Status**: Accepted
**Deciders**: Product Owner, Development Team
**Context**: Work Hierarchy Alignment Recommendation

---

## Context and Problem Statement

Obra currently uses non-standard terminology for work organization:
- "Milestone" used for "group of tasks" (incorrect - milestones should be zero-duration checkpoints)
- All work units are generic "Task" regardless of size or scope
- No clear distinction between large features (Epics) and deliverable units (Stories)
- Terminology doesn't align with industry standards (Agile, JIRA, Linear, etc.)

**Problem**: Confusing terminology limits communication, tooling integration, and scalability.

**Decision Required**: Should Obra adopt a standard work hierarchy framework?

---

## Decision Drivers

1. **Industry Standard Communication**: Team members, stakeholders, and external tools use Agile terminology
2. **Natural Fit for AI Orchestration**: Obra's iterative PROCEED/RETRY/CLARIFY loop maps perfectly to Agile Sprint workflow
3. **Tooling Integration**: Export/import with JIRA, Linear, Asana requires standard hierarchy
4. **Scalability**: Clear Epic → Story → Task hierarchy supports complex multi-feature projects
5. **Current Usage**: Obra already implements Epic-like behavior (`execute_milestone()` groups tasks in sessions)
6. **Prototype Phase**: Early enough to make breaking changes without user impact

---

## Considered Options

### Option 1: Keep Current Structure (Status Quo)
- Maintain "Project" and "Task" with no hierarchy
- Keep using "milestone" incorrectly
- **Result**: REJECTED - perpetuates confusion, limits growth

### Option 2: Traditional WBS (Work Breakdown Structure)
- Hierarchy: Project → Phase → Work Package → Task
- Focus on deliverables and phases
- **Result**: REJECTED - too rigid for iterative AI development, waterfall-oriented

### Option 3: Agile/Scrum Hierarchy ✅
- Hierarchy: Product → Epic → Story → Task → Subtask
- Focus on user value and iterative delivery
- **Result**: ACCEPTED - best fit for Obra's iterative orchestration

### Option 4: Hybrid WBS + Agile
- Support both frameworks
- **Result**: REJECTED - unnecessary complexity, Agile-only is sufficient

---

## Decision Outcome

**Chosen Option**: **Agile/Scrum Hierarchy (Option 3)**

### Work Hierarchy

```
Product (mapped to ProjectState)
  ↓
Epic (new - large feature spanning multiple sessions)
  ↓
Story (new - user-facing deliverable, 1 orchestration session)
  ↓
Task (existing - technical work to implement story)
  ↓
Subtask (existing - via parent_task_id FK)
```

**Plus**:
- **Milestone**: True milestone (zero-duration checkpoint marking Epic/Phase completion)
- **Sprint/Session**: Orchestration session executing multiple stories in Epic

### Key Terminology Changes

| Old Term | New Term | Definition |
|----------|----------|------------|
| Milestone (as task group) | Epic | Large feature spanning multiple stories |
| Task (any work unit) | Story | User-facing deliverable (1 session) |
| Task (technical work) | Task | Technical work implementing story |
| execute_milestone() | execute_epic() | Execute group of stories in Epic |
| - (didn't exist) | Milestone | Zero-duration checkpoint |

### Implementation Decisions

1. **Big Bang Migration**: Replace all terminology and schema at once (prototype phase allows this)
2. **No Story Points**: Use existing complexity estimates and code length predictions (sufficient for AI orchestration)
3. **Agile-Only**: No WBS hybrid support (simplicity over flexibility)
4. **Database Schema Updates**: Add TaskType enum, Epic/Story fields, Milestone table
5. **Terminology Replacement**: Update all code, docs, CLI commands

---

## Positive Consequences

✅ **Industry-Standard Terminology**
- "Epic" and "Story" universally understood
- Easier onboarding for new users
- Better communication with stakeholders

✅ **Natural Fit for AI Orchestration**
- Story = unit of work for Implementer
- Iteration = PROCEED/RETRY/CLARIFY loop
- Epic = multi-session feature
- Sprint/Session = orchestration session

✅ **Tooling Integration**
- Export to JIRA, Linear, Asana
- Import from standard PM tools
- Better reporting (velocity, burndown)

✅ **Clear Hierarchy**
- Epic → Story → Task provides 3 levels of granularity
- Subtask via parent_task_id for optional detail

✅ **Scalability**
- Complex projects with many features organized clearly
- Dependency tracking at Story level
- Milestone gates for quality control

✅ **Correct "Milestone" Usage**
- Milestones now mean checkpoints (correct!)
- No more confusion about "milestone as task group"

---

## Negative Consequences

❌ **Breaking Changes**
- All existing code using "milestone" must update
- Database migration required
- CLI commands change
- **Mitigation**: Prototype phase, no external users yet

❌ **Learning Curve**
- Team must learn Agile terminology if unfamiliar
- **Mitigation**: Comprehensive docs, examples

❌ **Migration Effort**
- ~30 files need updates
- Database schema changes
- Test updates
- **Mitigation**: Systematic migration plan, one-time cost

❌ **No Backward Compatibility**
- Old API calls will break
- **Mitigation**: Acceptable in prototype phase

---

## Validation

### Success Criteria

✅ Database schema includes Epic, Story, Task, Subtask, Milestone types
✅ All "milestone" references replaced with "epic" or "milestone" (correct usage)
✅ CLI supports `epic create`, `story create`, `milestone create`
✅ Documentation uses Agile terminology consistently
✅ Tests pass with new schema
✅ Example projects demonstrate Epic → Story → Task hierarchy

### Validation Plan

1. **Schema Migration**: Database includes all new models
2. **Code Update**: No references to old terminology remain
3. **Test Coverage**: All tests updated and passing
4. **Documentation**: All docs reflect new hierarchy
5. **Example**: Create sample project demonstrating Epic with 3 Stories

---

## Implementation Plan

**Implementation Document**: `docs/development/AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md`

**Estimated Effort**: Medium (3-5 days)
**Risk**: Low (prototype phase, comprehensive plan)
**Timeline**: v1.3.0 release

---

## Links

- **Work Breakdown Reference Guide**: `docs/research/work-breakdown-reference-guide.md`
- **Recommendation Analysis**: `docs/design/WORK_HIERARCHY_ALIGNMENT_RECOMMENDATION.md`
- **Implementation Plan**: `docs/development/AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md`
- **Related ADRs**:
  - ADR-009: Task Dependency System (M9)
  - ADR-011: Interactive Streaming Interface

---

## Notes

- Decision made during prototype phase (v1.2.x)
- No external users impacted by breaking changes
- Foundation for future PM tool integrations
- Aligns with iterative AI orchestration workflow
- Complexity estimates (from PHASE_6) replace story points

---

**Decision Status**: ✅ ACCEPTED

**Implementation Status**: 🚧 PLANNED (ADR created, implementation pending)

**Next Action**: Execute implementation plan in `AGILE_HIERARCHY_IMPLEMENTATION_PLAN.md`
