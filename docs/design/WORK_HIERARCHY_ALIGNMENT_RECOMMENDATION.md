# Work Hierarchy Alignment Recommendation

**Date**: November 5, 2025
**Status**: Proposal
**Reviewers**: Product Owner

---

## Executive Summary

**Recommendation**: **Adopt Agile/Scrum hierarchy with modifications** for Obra's work structure.

**Current State**: Obra has an **incomplete hybrid structure** - it supports hierarchical tasks but uses non-standard terminology ("milestones" for groups of tasks).

**Proposed State**: Align to **Agile/Scrum hierarchy** (Product → Epic → Story → Task → Subtask) with AI orchestration enhancements.

**Impact**: Moderate refactoring required (database schema changes, terminology updates, documentation).

**Benefits**:
- Industry-standard terminology → better communication
- Natural fit for iterative AI development
- Supports evolving requirements
- Better tooling integration (JIRA, Linear, etc.)

---

## Current Obra Structure (As-Built)

### Database Schema

```
ProjectState (models.py line 71)
    ├── id, project_name, description, working_directory
    ├── status: ACTIVE, PAUSED, COMPLETED, ARCHIVED
    └── tasks (one-to-many relationship)

Task (models.py line 129)
    ├── id, project_id, parent_task_id (self-referential FK!)
    ├── title, description, status, priority (1-10)
    ├── dependencies: JSON list of task IDs
    ├── assigned_to: HUMAN, LOCAL_LLM, CLAUDE_CODE, SYSTEM
    ├── retry_count, max_retries
    └── subtasks (backref relationship via parent_task_id)

Session (not shown but exists)
    ├── session_id, project_id, task_id
    ├── milestone_id (Optional[int]) ← NOT IN DATABASE YET
    └── Tracks Claude Code sessions
```

### Key Findings

✅ **Already Implemented:**
- Hierarchical tasks (`parent_task_id` + `subtasks` relationship)
- Task dependencies (M9 feature)
- Project-level organization
- Iterative execution per task (max_iterations_per_task)
- Session management

❌ **Missing or Non-Standard:**
- **No Milestones Table**: Orchestrator.py line 665 comment: "We don't have a milestone table yet, but placeholder for future"
- **No Epic/Story Distinction**: All work units are "Task" regardless of size
- **Confusing Terminology**: "Milestone" used for "group of tasks" instead of "checkpoint"
- **No Story Points**: Priority 1-10 doesn't map to complexity/effort
- **No Sprint Concept**: Milestones are used but not time-boxed

---

## Analysis: Which Framework Fits Obra Best?

### Option 1: Traditional WBS

❌ **Not Recommended**

**Pros:**
- Clear upfront planning
- Good for fixed scope projects

**Cons:**
- **Poor fit for AI orchestration**: Requirements evolve based on implementer output
- **Rigid**: Doesn't support iterative refinement loops (RETRY/CLARIFY decisions)
- **Too sequential**: Obra works iteratively, not waterfall
- **Heavy planning overhead**: AI development is exploratory

### Option 2: Agile/Scrum ✅

✅ **RECOMMENDED**

**Pros:**
- **Perfect match for iterative development**: Obra's PROCEED/RETRY/CLARIFY loop = Sprint workflow
- **Handles evolving requirements**: Quality gates drive next iteration
- **User-centric**: Stories focus on deliverable value
- **Industry standard**: Better communication with human teams
- **Flexible**: Supports changing scope based on orchestrator feedback

**Cons:**
- Requires schema changes (add Epic, Story types)
- Need to update terminology throughout codebase
- More complex than current simple structure

---

## Recommended Structure

### Proposed Hierarchy

```
Portfolio (Optional - Future)
   ↑
Product ← Maps to current ProjectState
   ↑
Epic ← NEW: Large feature set (3-15 sprints worth of work)
   ↑
Story/Feature ← NEW: User-facing deliverable (1 sprint)
   ↑
Task ← CURRENT: Technical work to implement story
   ↑
Subtask ← CURRENT: Via parent_task_id (optional granularity)
```

### Obra-Specific Additions

**Sprint** → **Orchestration Session**
- Time-boxed iteration (not calendar-based, but iteration-count-based)
- Each story has max_iterations (default: 10)
- Orchestrator decides PROCEED/RETRY/CLARIFY each iteration

**Milestone** → **True Milestone** (zero-duration checkpoint)
- Epic completion gate
- Phase boundary marker
- Quality gate approval

**Velocity** → **Orchestration Velocity**
- Average story points completed per session
- Tracks orchestrator efficiency over time

---

## Implementation Plan

### Phase 1: Database Schema Updates

**Add `TaskType` Enum:**
```python
class TaskType(str, enum.Enum):
    EPIC = 'epic'           # Large feature spanning multiple stories
    STORY = 'story'         # User-facing deliverable (1 session)
    TASK = 'task'           # Technical work (current default)
    SUBTASK = 'subtask'     # Granular step
```

**Update Task Model:**
```python
class Task(Base):
    # ... existing fields ...

    # NEW: Task type and sizing
    task_type = Column(
        Enum(TaskType),
        nullable=False,
        default=TaskType.TASK,
        index=True
    )
    story_points = Column(Integer, nullable=True)  # Fibonacci: 1,2,3,5,8,13,21

    # NEW: Epic/Story tracking
    epic_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)
    story_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)

    # EXISTING: Keep parent_task_id for subtask hierarchy
    parent_task_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)
```

**Add Milestone Model:**
```python
class Milestone(Base):
    """True milestone - zero-duration checkpoint."""
    __tablename__ = 'milestone'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    target_date = Column(DateTime, nullable=True)
    achieved_at = Column(DateTime, nullable=True)

    # What must be complete for this milestone
    required_epic_ids = Column(JSON, default=list)  # [epic_id, epic_id, ...]

    # Status
    achieved = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
```

**Add Sprint/Session Enhancement:**
```python
class Session(Base):  # (Already exists, enhance)
    # ... existing fields ...

    # NEW: Sprint-like metadata
    sprint_number = Column(Integer, nullable=True)
    sprint_goal = Column(Text, nullable=True)
    planned_story_points = Column(Integer, nullable=True)
    completed_story_points = Column(Integer, nullable=True)
```

### Phase 2: Terminology Updates

**Rename Methods:**
```python
# orchestrator.py
execute_milestone()     → execute_sprint()  or  execute_epic()
_build_milestone_context() → _build_sprint_context()
_start_milestone_session() → _start_sprint_session()
_end_milestone_session()   → _end_sprint_session()
```

**Update Documentation:**
- Replace "milestone" → "epic" or "sprint" (context dependent)
- Add "story" as primary work unit
- Document story point estimation guidelines

### Phase 3: API/CLI Updates

**Update CLI Commands:**
```bash
# OLD (current)
obra task create "Implement auth"

# NEW (Agile-aligned)
obra epic create "User Authentication"
obra story create "Email/password login" --epic 5 --points 5
obra task create "Create login API endpoint" --story 12
```

**Backward Compatibility:**
```python
# Keep old commands as aliases
obra milestone create → obra epic create (with deprecation warning)
obra task create → obra story create (if no parent, otherwise task)
```

---

## Migration Strategy

### Option A: Big Bang Migration (NOT RECOMMENDED)
- All at once schema change
- High risk, requires downtime
- Difficult rollback

### Option B: Gradual Migration ✅ RECOMMENDED

**Step 1: Add Opt-In Fields (v1.3.0)**
- Add `task_type`, `story_points`, `epic_id`, `story_id` as NULLABLE
- Default all existing tasks to `task_type=TASK`
- No breaking changes
- Users can start using new fields voluntarily

**Step 2: Dual API (v1.3.x)**
- Support both old and new commands
- Map old commands to new schema
- Log deprecation warnings

**Step 3: Add Milestone Table (v1.4.0)**
- Create Milestone model
- Migrate any "milestone_id" references from sessions

**Step 4: Enforce Hierarchy (v2.0.0 - Breaking)**
- Make task_type REQUIRED
- Enforce Epic → Story → Task hierarchy rules
- Remove deprecated commands

---

## Terminology Mapping

### Before (Current Obra)

| Obra Term | What It Actually Is |
|-----------|-------------------|
| Project | Project (correct) |
| Milestone | Group of tasks (INCORRECT - not a checkpoint!) |
| Task | Any unit of work (too generic) |
| Subtask | Child task via parent_task_id (correct) |

### After (Agile-Aligned)

| Agile Term | Obra Mapping | Example |
|------------|--------------|---------|
| Product | ProjectState | "E-commerce Platform" |
| Epic | Task with task_type=EPIC | "Shopping Cart Experience" (23 pts, 6 stories) |
| Story | Task with task_type=STORY | "Add items to cart" (5 pts, 1 sprint) |
| Task | Task with task_type=TASK | "Create 'Add to Cart' button UI" (4 hours) |
| Subtask | Task with parent_task_id | "Write tests for cart functionality" |
| Sprint | Session/Iteration | Execute epic with max_iterations=10 |
| Milestone | Milestone model | ✓ Epic: Shopping Cart Complete |

---

## Example: Before vs After

### Before (Current)

```python
# Create "milestone" (actually a group of tasks)
obra project create "E-commerce Site"
obra task create "Build shopping cart"
obra task create "Add to cart button"
obra task create "Cart page UI"
obra task create "Checkout flow"

# Execute (no hierarchy, no sizing)
obra orchestrate --project 1 --tasks 1,2,3,4
```

### After (Agile-Aligned)

```python
# Create proper hierarchy
obra project create "E-commerce Site"

# Epic (large feature set)
obra epic create "Shopping Cart Experience" --points 23

# Stories under epic
obra story create "Add items to cart" --epic 1 --points 5
obra story create "View cart contents" --epic 1 --points 3
obra story create "Update quantities" --epic 1 --points 3
obra story create "Remove from cart" --epic 1 --points 2
obra story create "Apply discount codes" --epic 1 --points 5

# Tasks under story (auto-created or manual)
obra task create "Create 'Add to Cart' button UI" --story 2
obra task create "Implement cart state management" --story 2

# Execute with proper iteration management
obra sprint execute --epic 1 --max-iterations-per-story 10

# True milestone
obra milestone create "Shopping Cart Complete" --requires-epic 1
```

---

## Benefits of Alignment

### 1. **Better Communication**
- Standard terminology used by PMs, developers, stakeholders
- No confusion: "milestone" means checkpoint, not "group of tasks"
- Easier onboarding for new users

### 2. **Natural Fit for AI Orchestration**
- **Story** = Unit of work Implementer executes
- **Iteration** = PROCEED/RETRY/CLARIFY loop
- **Sprint** = Orchestration session across multiple stories
- **Epic** = Large feature requiring multiple sessions

### 3. **Tooling Integration**
- Export to JIRA, Linear, Asana
- Import from standard project management tools
- Better reporting (burndown charts, velocity tracking)

### 4. **Scalability**
- Clear hierarchy for complex projects
- Story points enable better estimation
- Sprint goals drive focus

### 5. **Agile Best Practices**
- Definition of Done (quality gates)
- Velocity tracking (orchestration efficiency)
- Retrospectives (analyze failed iterations)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Breaking changes for existing users** | High | Gradual migration with backward compatibility (Option B) |
| **Learning curve for new terminology** | Medium | Comprehensive docs, examples, migration guide |
| **Database migration complexity** | Medium | Use nullable fields initially, enforce later |
| **Performance impact from complex queries** | Low | Index epic_id, story_id, task_type columns |

---

## Recommended Next Steps

1. **Review and Approve Proposal** ✋ (You are here)
   - Stakeholder feedback on Agile alignment
   - Decision: Approve, modify, or reject

2. **Create ADR** (If approved)
   - ADR-013: Adopt Agile/Scrum Work Hierarchy
   - Document rationale, alternatives considered

3. **Schema Design** (v1.3.0)
   - Detailed database migration plan
   - SQL scripts for adding new fields

4. **Implementation** (v1.3.x)
   - Add TaskType enum
   - Update Task model with nullable fields
   - Create Milestone model
   - Add dual API support

5. **Documentation** (v1.3.x)
   - User guide: "Working with Epics and Stories"
   - Migration guide: "Upgrading from Obra 1.2.x"
   - Update all examples

6. **Gradual Enforcement** (v2.0.0)
   - Make task_type required
   - Enforce hierarchy rules
   - Remove deprecated APIs

---

## Open Questions

1. **Should we support both WBS AND Agile hierarchies?**
   - Pro: Flexibility for different project types
   - Con: More complexity, harder to maintain
   - Recommendation: **Agile-only** (simpler, better fit)

2. **How granular should task_type be?**
   - Option A: EPIC, STORY, TASK, SUBTASK (4 levels)
   - Option B: EPIC, STORY, TASK (3 levels, use parent_task_id for subtasks)
   - Recommendation: **Option A** (explicit types clearer)

3. **Should story points be required for Stories?**
   - Pro: Forces estimation discipline
   - Con: Some users may not want to estimate
   - Recommendation: **Optional** initially, document benefits

4. **Deprecation timeline for old API?**
   - Recommendation: **2 major versions** (v1.3 → v1.4 → v2.0)
   - v1.3: Add new, keep old (warnings)
   - v1.4: Both work, deprecation notices
   - v2.0: Remove old API

---

## Conclusion

**Obra's current structure is a good foundation**, but using non-standard terminology ("milestones" for task groups) creates confusion and limits integration with standard PM tools.

**Adopting Agile/Scrum hierarchy** provides:
- ✅ Industry-standard terminology
- ✅ Natural fit for iterative AI orchestration
- ✅ Better communication and tooling support
- ✅ Scalability for complex projects

**Recommendation**: **Proceed with gradual migration to Agile/Scrum hierarchy** starting in v1.3.0.

---

**Decision**: [ ] Approved  [ ] Approved with changes  [ ] Rejected  [ ] Defer

**Feedback**:


**Next Action**: Create ADR-013 if approved

---

*Document prepared by: Claude (AI Assistant)*
*Reviewed by: [Your Name]*
