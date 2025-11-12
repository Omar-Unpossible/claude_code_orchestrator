# Quality Assurance Documentation

This directory contains documentation and logs related to manual testing, quality assurance, and issue tracking for the Obra project.

## Overview

The Quality directory provides tools for **longitudinal analysis** of issues discovered during manual testing. Unlike automated tests (which catch regressions), this system helps identify:

- **Recurring patterns** across multiple issues
- **Architectural concerns** requiring design changes
- **User experience friction** not caught by unit tests
- **System-level behaviors** emerging from component interactions

## Files in This Directory

### MANUAL_TESTING_LOG.yaml
**The primary issue log** - A structured YAML file containing all issues discovered during manual testing.

**Purpose**: Durable record of issues for pattern analysis and architectural insights

**Update Frequency**: Add entries as issues are discovered; update as they're resolved

**Format**: Structured YAML with standardized fields (see ISSUE_LOG_GUIDE.md)

### ISSUE_LOG_GUIDE.md
**Comprehensive guide** for using the Manual Testing Issue Log.

**Contents**:
- When and how to log issues
- Field definitions and requirements
- Workflow from discovery to resolution
- Pattern analysis techniques
- Integration with ADRs and CHANGELOG

**Audience**: Anyone performing manual testing or quality analysis

### ISSUE_TEMPLATE.yaml
**Quick-reference template** for adding new issues to the log.

**Usage**: Copy the template when logging a new issue to ensure all fields are included

**Purpose**: Standardize issue reporting and reduce errors

### analyze_issues.py
**Analysis utility script** for generating statistics and insights from the log.

**Features**:
- Category and severity breakdowns
- Resolution time analysis
- Pattern detection
- Trend visualization

**Usage**: `python docs/quality/analyze_issues.py`

## Relationship to Other Documentation

### vs. Automated Tests (`tests/`)
- **Automated Tests**: Catch known regressions, verify expected behavior
- **Manual Testing Log**: Discover unknown issues, identify patterns, guide architecture

**Use Both**: Automated tests for fast feedback; manual testing for exploration

### vs. Architecture Decision Records (`docs/decisions/`)
- **ADRs**: Formal decisions about architecture and design
- **Manual Testing Log**: Raw observations that may lead to ADRs

**Workflow**: Log → Pattern Analysis → ADR Creation → Implementation

### vs. CHANGELOG (`CHANGELOG.md`)
- **CHANGELOG**: User-facing record of changes and fixes
- **Manual Testing Log**: Internal tracking for quality improvement

**Connection**: Reference issue IDs in CHANGELOG entries for traceability

### vs. Phase Reports (`docs/development/phase-reports/`)
- **Phase Reports**: Summaries of development work completed
- **Manual Testing Log**: Ongoing tracking of quality issues

**Timing**: Phase reports are retrospective; issue log is continuous

## Quick Start

### Logging Your First Issue

1. **Encounter an issue during manual testing**
   ```bash
   # Example: You notice StateManager is slow with large transactions
   ```

2. **Open the log file**
   ```bash
   vim docs/quality/MANUAL_TESTING_LOG.yaml
   ```

3. **Copy the template**
   ```bash
   # From docs/quality/ISSUE_TEMPLATE.yaml
   ```

4. **Fill in the fields**
   ```yaml
   - id: "ISSUE-001"  # Next sequential number
     title: "StateManager slow with large transactions"
     # ... fill in remaining fields
   ```

5. **Save and commit**
   ```bash
   git add docs/quality/MANUAL_TESTING_LOG.yaml
   git commit -m "docs: Log ISSUE-001 - StateManager performance"
   ```

### Analyzing Patterns

After accumulating 10+ issues:

1. **Run the analysis script**
   ```bash
   python docs/quality/analyze_issues.py
   ```

2. **Review output for patterns**
   ```
   Issues by Category:
     STATE_MANAGEMENT: 5
     AGENT_COMMUNICATION: 3
     VALIDATION: 2

   Recurring Themes Detected:
     - Transaction timeout issues (3 occurrences)
   ```

3. **Create ADRs for architectural concerns**
   ```bash
   # If pattern suggests a design change
   vim docs/decisions/ADR-XXX-improve-transaction-management.md
   ```

## Workflow Integration

### Daily Development
```
Write code → Manual test → Encounter issue → Log it → Continue
```

### Weekly Review
```
Review log → Identify quick wins → Fix and update status
```

### Monthly Analysis
```
Run analysis script → Find patterns → Discuss architectural implications → Create ADRs if needed
```

### Quarterly Review
```
Export statistics → Update pattern analysis → Archive old issues → Reflect on quality trends
```

## Best Practices

### ✅ Do This
- Log issues as you find them (while context is fresh)
- Be specific in reproduction steps
- Think about root causes, not just symptoms
- Cross-reference related issues
- Update status when issues are resolved
- Review patterns monthly

### ❌ Avoid This
- Waiting to log multiple issues at once (you'll forget details)
- Skipping reproduction steps (makes verification hard)
- Inflating severity to get attention (reduces signal)
- Logging issues already tracked elsewhere (duplication)
- Never reviewing the log (defeats the purpose)
- Treating this as a "bug database" (it's for analysis, not just tracking)

## Categories Reference

Choose the category that best matches the affected component:

| Category | Examples |
|----------|----------|
| STATE_MANAGEMENT | StateManager bugs, transaction issues, database problems |
| ORCHESTRATION | Core loop issues, iteration logic, task execution |
| AGENT_COMMUNICATION | Claude Code subprocess, session management, IPC |
| LLM_INTEGRATION | Ollama connection, Qwen responses, prompt issues |
| VALIDATION | ResponseValidator, QualityController, ConfidenceScorer bugs |
| DECISION_ENGINE | DecisionEngine logic, threshold issues, action selection |
| CONFIGURATION | Config loading, profile issues, settings validation |
| CLI | Command-line parsing, argument validation, output formatting |
| INTERACTIVE_MODE | Command processor, input handling, checkpoints |
| GIT_INTEGRATION | Commits, branches, PR creation, Git operations |
| NATURAL_LANGUAGE | Intent classification, entity extraction, NL commands |
| AGILE_WORKFLOW | Epic/story/milestone issues, task hierarchy |
| PROJECT_INFRASTRUCTURE | Doc maintenance, freshness tracking, auto-updates |
| PERFORMANCE | Speed issues, resource usage, optimization opportunities |
| ARCHITECTURE | Design concerns, technical debt, pattern violations |

## Metrics Tracked

The log supports analysis of:

- **Issue Volume**: Total issues, open vs. closed over time
- **Category Distribution**: Which components have most issues
- **Severity Distribution**: Are we catching critical issues early?
- **Resolution Time**: Average time from open to closed
- **Recurring Patterns**: Issues that appear multiple times
- **Architectural Concerns**: Design issues needing ADRs
- **Quality Trends**: Is quality improving or degrading?

## Tools & Scripts

### analyze_issues.py
Location: `docs/quality/analyze_issues.py`

Features:
- Generate category breakdown
- Calculate severity distribution
- Detect recurring patterns
- Compute resolution time averages
- Export to CSV or JSON
- Create trend charts (if matplotlib installed)

Usage:
```bash
# Basic analysis
python docs/quality/analyze_issues.py

# Export to CSV
python docs/quality/analyze_issues.py --export csv

# Generate trend chart
python docs/quality/analyze_issues.py --chart
```

### Future Tools
- **Pattern detection AI**: Use LLM to detect subtle patterns
- **ADR generator**: Auto-suggest ADRs from issue clusters
- **Dashboard**: Web-based visualization of quality metrics
- **Integration with GitHub Issues**: Sync for visibility

## FAQ

### Q: When should I use this vs. GitHub Issues?
**A**: Use this log for **pattern analysis during manual testing**. Use GitHub Issues for **user-reported bugs** and **planned features**. This log is internal for quality insights.

### Q: Do I need to log every tiny issue?
**A**: No. Focus on issues that:
- Affect functionality (even minor)
- Reveal potential patterns
- Suggest architectural concerns
- Impact user experience

Skip truly trivial issues like typos in comments.

### Q: How often should I review patterns?
**A**:
- **Weekly**: Quick scan for critical issues
- **Monthly**: Deeper analysis for patterns
- **Quarterly**: Comprehensive review with ADR creation

### Q: What if I find an issue that's already fixed?
**A**: Still log it! Mark status as CLOSED and note when it was fixed. This helps track historical issues and validate fixes.

### Q: Can I change the log format?
**A**: Yes, but update `log_version` in metadata and document changes in ISSUE_LOG_GUIDE.md. Migrate existing issues to new format.

### Q: Should I log test failures?
**A**: No - test failures are tracked by pytest. Only log issues **discovered during manual testing** that tests didn't catch.

---

## Getting Started

1. ✅ Read ISSUE_LOG_GUIDE.md (comprehensive guide)
2. ✅ Review ISSUE_TEMPLATE.yaml (quick reference)
3. ✅ Open MANUAL_TESTING_LOG.yaml (the log file)
4. ✅ Start manual testing and log your first issue!

---

**Version**: 1.0.0
**Created**: 2025-11-11
**Maintained By**: Project Quality Team

For questions or improvements to this system, contact the project maintainer or open a GitHub Issue.
