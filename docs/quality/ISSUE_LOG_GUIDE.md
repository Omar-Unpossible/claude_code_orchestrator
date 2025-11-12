# Manual Testing Issue Log Guide

## Overview

The Manual Testing Issue Log (`MANUAL_TESTING_LOG.yaml`) provides a structured, durable record of issues discovered during manual testing of Obra. This log enables:

1. **Longitudinal Analysis**: Track patterns and trends over time
2. **Root Cause Analysis**: Identify systemic vs. isolated issues
3. **Architectural Insights**: Spot design weaknesses requiring ADRs
4. **Quality Metrics**: Measure issue frequency, severity distribution, resolution time

## Purpose & Scope

### In Scope
- Issues discovered during manual testing
- Performance observations during real-world usage
- UX friction points encountered by users
- Architectural concerns identified through use
- Enhancement ideas triggered by actual workflows

### Out of Scope
- Automated test failures (covered by pytest suite)
- Code review findings (use PR comments)
- Planned features (use GitHub Issues or ADRs)
- Security vulnerabilities (report separately with urgency)

## When to Log an Issue

Log an issue when:
- ✅ You encounter unexpected behavior during manual testing
- ✅ System performs differently than documented
- ✅ Workflow feels clunky or confusing
- ✅ You identify a potential architectural concern
- ✅ Performance degrades noticeably
- ✅ You discover an edge case not covered by tests

Don't log when:
- ❌ Issue is already tracked in another system
- ❌ It's a planned feature (not a defect)
- ❌ You're just exploring code (wait until you find a concrete issue)

## Log Format

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Sequential ID: `ISSUE-001`, `ISSUE-002`, etc. |
| `title` | String | Concise summary (5-10 words) |
| `description` | Text | Detailed explanation with context |
| `timestamp` | ISO 8601 | When issue was discovered |
| `reporter` | String | Who found it (your name or "System") |
| `category` | Enum | System component (see categories below) |
| `severity` | Enum | Impact level (CRITICAL/HIGH/MEDIUM/LOW) |
| `type` | Enum | Issue type (BUG/PERFORMANCE/UX/ARCHITECTURAL/ENHANCEMENT) |
| `status` | Enum | Current state (OPEN/IN_PROGRESS/RESOLVED/CLOSED/WONT_FIX) |

### Optional but Recommended

| Field | Type | Description |
|-------|------|-------------|
| `version` | String | Obra version when issue found |
| `environment` | Object | OS, Python, LLM, Agent details |
| `steps_to_reproduce` | List | Exact steps to trigger issue |
| `expected_behavior` | Text | What should have happened |
| `actual_behavior` | Text | What actually happened |
| `affected_components` | List | Source files involved |
| `root_cause` | Text | Analysis of why this happened |
| `impact_analysis` | Object | User/system impact, frequency |
| `resolution` | Object | How fixed, commit SHA, verification |
| `related_links` | Object | ADRs, commits, PRs, issues |
| `tags` | List | Keywords for pattern analysis |
| `follow_up_needed` | Boolean | Requires additional work? |
| `notes` | Text | Additional context/observations |

## Categories (Aligned with Architecture)

Choose the primary component affected:

- `STATE_MANAGEMENT` - StateManager, database, transactions, rollback
- `ORCHESTRATION` - Core orchestration loop, iteration logic, task execution
- `AGENT_COMMUNICATION` - Claude Code integration, subprocess, session management
- `LLM_INTEGRATION` - Ollama, Qwen, prompt engineering, response parsing
- `VALIDATION` - ResponseValidator, QualityController, ConfidenceScorer
- `DECISION_ENGINE` - DecisionEngine logic, thresholds, action selection
- `CONFIGURATION` - Config loading, profiles, settings, validation
- `CLI` - Command-line interface, argument parsing, subcommands
- `INTERACTIVE_MODE` - Command processor, input manager, checkpoints
- `GIT_INTEGRATION` - GitManager, commits, branches, PR creation
- `NATURAL_LANGUAGE` - NL command interface, intent classification, entity extraction
- `AGILE_WORKFLOW` - Epics, stories, milestones, task hierarchy
- `PROJECT_INFRASTRUCTURE` - Documentation maintenance, freshness tracking
- `PERFORMANCE` - Speed, resource usage, memory, optimization
- `ARCHITECTURE` - Design concerns, patterns, technical debt

## Severity Levels

| Level | Criteria | Examples |
|-------|----------|----------|
| `CRITICAL` | System crash, data loss, security vulnerability | Database corruption, WSL2 crash, API key leak |
| `HIGH` | Major functionality broken, blocks workflow | Can't execute tasks, StateManager deadlock |
| `MEDIUM` | Functionality impaired, workaround exists | Slow validation, confusing error message |
| `LOW` | Minor issue, cosmetic, enhancement | Typo in output, missing color in CLI |

## Issue Types

| Type | Description | Examples |
|------|-------------|----------|
| `BUG` | Functional defect | Feature doesn't work as documented |
| `PERFORMANCE` | Speed or resource issue | Takes 5min instead of 30sec |
| `UX` | User experience problem | Confusing prompts, unclear workflow |
| `ARCHITECTURAL` | Design or pattern concern | Component coupling, unclear boundaries |
| `ENHANCEMENT` | Feature request or improvement | "Would be nice if..." |
| `DOCUMENTATION` | Docs incorrect or missing | README out of date, missing guide |

## Status Values

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `OPEN` | Newly reported | Triage and assign priority |
| `IN_PROGRESS` | Being worked on | Continue investigation/fix |
| `RESOLVED` | Fixed/implemented | Verify in testing |
| `CLOSED` | Verified complete | None - done |
| `WONT_FIX` | Intentional or out of scope | Document rationale |
| `DUPLICATE` | Duplicate of another issue | Link to original |

## Workflow

### 1. Discovering an Issue

When you encounter an issue during manual testing:

1. **Stop and Document**: Don't just fix it immediately - record what you found
2. **Assign ID**: Use the next sequential number (`ISSUE-001`, `ISSUE-002`, etc.)
3. **Capture Context**: Note version, environment, what you were doing
4. **Record Steps**: Write down exact reproduction steps while fresh
5. **Set Severity**: Assess impact honestly (most issues are MEDIUM or LOW)

### 2. Investigating the Issue

Before or during the fix:

1. **Identify Root Cause**: Don't just treat symptoms
2. **Check for Patterns**: Is this related to other issues?
3. **Assess Architectural Impact**: Does this reveal a design problem?
4. **List Affected Components**: Help with impact analysis later

### 3. Resolving the Issue

When implementing a fix:

1. **Update Status**: `OPEN` → `IN_PROGRESS` when you start
2. **Document Approach**: Record how you're fixing it
3. **Link to Changes**: Add commit SHA or PR number
4. **Update Status**: `IN_PROGRESS` → `RESOLVED` when fixed
5. **Verify**: Test that fix works, update status to `CLOSED`

### 4. Periodic Review

Every 2-4 weeks (or after major milestones):

1. **Analyze Patterns**: Review all issues for trends
2. **Update Pattern Analysis**: Add insights to bottom of log
3. **Create ADRs**: Convert architectural concerns to formal decisions
4. **Refine Process**: Improve logging based on what's useful

## Pattern Analysis

The `pattern_analysis` section at the bottom of the log tracks trends:

### Recurring Themes
Identify issues that keep happening:
```yaml
recurring_themes:
  - theme: "Session lock conflicts"
    occurrences: 3
    issues: ["ISSUE-005", "ISSUE-012", "ISSUE-018"]
    recommended_action: "Consider ADR for session architecture"
```

### Architectural Concerns
Flag design issues requiring ADRs:
```yaml
architectural_concerns:
  - concern: "StateManager becoming too complex"
    related_issues: ["ISSUE-007", "ISSUE-015"]
    severity: "HIGH"
    proposed_adr: "Split StateManager into multiple managers"
```

### Suggested Improvements
Track enhancement ideas:
```yaml
suggested_improvements:
  - improvement: "Add progress indicators for long operations"
    benefit: "Better UX, reduces user confusion"
    effort: "LOW"
    priority: "MEDIUM"
```

## Example Issue Entry

```yaml
- id: "ISSUE-001"
  title: "StateManager transaction timeout during large epic execution"
  description: |
    When executing an epic with 10+ stories, the StateManager transaction
    times out after 30 seconds, causing the orchestration to fail midway.

    This happened during manual testing of the Agile workflow feature with
    a large epic containing 12 stories.

  timestamp: "2025-11-11T14:32:00Z"
  reporter: "Omar"
  category: "STATE_MANAGEMENT"
  severity: "HIGH"
  type: "BUG"
  status: "RESOLVED"

  version: "v1.3.0"
  environment:
    os: "WSL2 Ubuntu 22.04"
    python: "3.11.6"
    llm_provider: "Ollama/Qwen 2.5 Coder 32B"
    agent: "Claude Code CLI"

  steps_to_reproduce:
    - "Create project: obra project create 'Test Project'"
    - "Create large epic: obra epic create 'Large Feature' --project 1"
    - "Add 12 stories to epic using CLI"
    - "Execute epic: obra epic execute 1 --project 1"
    - "Observe timeout after 6th story completes"

  expected_behavior: "Epic should execute all stories sequentially without timeout"
  actual_behavior: "Transaction timeout after 30 seconds, partial completion only"

  affected_components:
    - "src/state_manager.py"
    - "src/orchestrator.py (execute_epic method)"

  root_cause: |
    StateManager uses a single transaction for the entire epic execution,
    which exceeds the default SQLite timeout (30s) for large epics.

    The transaction is held open from epic start to epic end, locking the
    database for too long.

  impact_analysis:
    user_impact: "Cannot execute large epics (10+ stories), severely limits workflow"
    system_impact: "Database locks prevent other operations during epic execution"
    frequency: "Always occurs with epics containing >8 stories"

  resolution:
    approach: |
      Changed epic execution to use separate transactions per story instead
      of one transaction for entire epic. Added checkpoint after each story.
    implemented_in: "commit-abc123"
    verified_date: "2025-11-11"
    verification_notes: "Tested with 15-story epic, completed successfully in 45min"

  related_links:
    adr: ["ADR-013"]
    commits: ["abc123"]
    prs: []
    issues: []

  tags:
    - "transaction-management"
    - "agile-workflow"
    - "database"
    - "scalability"

  follow_up_needed: true
  follow_up_tasks:
    - "Add configurable transaction timeout to config"
    - "Document transaction boundaries in architecture docs"

  notes: |
    This issue revealed a broader concern about transaction scope management
    in StateManager. Consider adding a transaction monitoring decorator.
```

## Tips for Effective Logging

### Be Specific
❌ Bad: "Agent doesn't work"
✅ Good: "Claude Code subprocess hangs on tasks with >10 file changes"

### Capture Context
❌ Bad: Just list the error message
✅ Good: Describe what you were doing, system state, recent changes

### Think Architecturally
Ask yourself: "Is this a one-off bug or a symptom of a design issue?"

### Link Related Issues
If you find similar issues, cross-reference them - patterns emerge!

### Update Promptly
When you fix an issue, update the log immediately while details are fresh

### Be Honest About Severity
Don't inflate severity - it reduces signal. Most issues are MEDIUM or LOW.

## Analysis & Reporting

### Generate Statistics

Use a simple script to analyze the log:

```python
import yaml

with open('docs/quality/MANUAL_TESTING_LOG.yaml') as f:
    log = yaml.safe_load(f)

issues = log['issues']

# Category breakdown
categories = {}
for issue in issues:
    cat = issue['category']
    categories[cat] = categories.get(cat, 0) + 1

print("Issues by Category:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")

# Severity distribution
severities = {}
for issue in issues:
    sev = issue['severity']
    severities[sev] = severities.get(sev, 0) + 1

print("\nIssues by Severity:")
for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
    print(f"  {sev}: {severities.get(sev, 0)}")
```

### Quarterly Review

Every 3 months (or after major milestones):

1. Export all issues to a report
2. Identify the top 3 recurring patterns
3. Create ADRs for architectural concerns
4. Update system overview with lessons learned
5. Archive resolved issues if log gets too large

## Integration with Other Processes

### Relationship to ADRs
- **Issue Log**: Captures raw observations during testing
- **ADRs**: Formalize architectural decisions based on patterns in the log

When an issue reveals a design concern, create an ADR referencing the issue(s).

### Relationship to Automated Tests
- **Automated Tests**: Catch regressions in known scenarios
- **Manual Testing**: Discover edge cases, UX issues, integration problems

When manual testing finds a bug, consider adding an automated test for it.

### Relationship to CHANGELOG
- **Issue Log**: Internal tracking for quality analysis
- **CHANGELOG**: User-facing record of changes

Reference issue IDs in CHANGELOG entries if relevant.

## Maintenance

### Archiving Old Issues
When the log exceeds 100 issues:
1. Create `MANUAL_TESTING_LOG_ARCHIVE_YYYY.yaml`
2. Move CLOSED issues older than 6 months to archive
3. Keep pattern analysis in main log
4. Update metadata (total_issues, open_issues)

### Log Format Updates
If you need to change the schema:
1. Update `log_version` in metadata
2. Document changes in this guide
3. Migrate existing issues to new format
4. Keep old format in archive files

---

**Version**: 1.0.0
**Created**: 2025-11-11
**Last Updated**: 2025-11-11

For questions or suggestions about this logging system, see the project maintainer.
