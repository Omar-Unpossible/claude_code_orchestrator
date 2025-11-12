# Manual Testing Issue Log - Quick Start

**Purpose**: Track issues discovered during manual testing for longitudinal analysis and architectural insights.

## ⚡ Quick Actions

### Log a New Issue

1. **Open the log**: `vim docs/quality/MANUAL_TESTING_LOG.yaml`
2. **Copy template**: From `docs/quality/ISSUE_TEMPLATE.yaml`
3. **Fill in details**: At minimum: id, title, description, timestamp, category, severity, type, status
4. **Save and commit**: `git commit -m "docs: Log ISSUE-XXX - brief title"`

### Analyze Issues

```bash
# Basic analysis
python3 docs/quality/analyze_issues.py

# Export to CSV
python3 docs/quality/analyze_issues.py --export csv

# Export to JSON
python3 docs/quality/analyze_issues.py --export json

# Deep pattern analysis
python3 docs/quality/analyze_issues.py --patterns
```

### Review Patterns

```bash
# Monthly: Look for recurring themes
grep -A5 "pattern_analysis:" docs/quality/MANUAL_TESTING_LOG.yaml

# Quarterly: Create ADRs from architectural concerns
python3 docs/quality/analyze_issues.py --patterns | grep -A10 "ARCHITECTURAL"
```

## 📋 Field Quick Reference

### Required Fields
- `id`: Sequential number (ISSUE-001, ISSUE-002, ...)
- `title`: 5-10 words
- `description`: Detailed explanation
- `timestamp`: ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
- `reporter`: Your name
- `category`: Component affected (see below)
- `severity`: CRITICAL/HIGH/MEDIUM/LOW
- `type`: BUG/PERFORMANCE/UX/ARCHITECTURAL/ENHANCEMENT/DOCUMENTATION
- `status`: OPEN/IN_PROGRESS/RESOLVED/CLOSED/WONT_FIX/DUPLICATE

### Categories (Choose One)
- `STATE_MANAGEMENT` - StateManager, database, transactions
- `ORCHESTRATION` - Core loop, iteration logic
- `AGENT_COMMUNICATION` - Claude Code subprocess
- `LLM_INTEGRATION` - Ollama, Qwen, prompts
- `VALIDATION` - Validators, quality control
- `DECISION_ENGINE` - DecisionEngine logic
- `CONFIGURATION` - Config, profiles, settings
- `CLI` - Command-line interface
- `INTERACTIVE_MODE` - Command processor, input
- `GIT_INTEGRATION` - GitManager, commits
- `NATURAL_LANGUAGE` - NL commands, intent
- `AGILE_WORKFLOW` - Epics, stories, milestones
- `PROJECT_INFRASTRUCTURE` - Doc maintenance
- `PERFORMANCE` - Speed, resource usage
- `ARCHITECTURE` - Design concerns

### Severity Guidelines
- `CRITICAL`: System crash, data loss, security
- `HIGH`: Major functionality broken, blocks workflow
- `MEDIUM`: Impaired functionality, workaround exists
- `LOW`: Minor issue, cosmetic

## 🔄 Workflow

```
Discover Issue → Log It → Investigate → Fix → Update Status → Close
     ↓             ↓          ↓           ↓         ↓           ↓
   Testing      OPEN    IN_PROGRESS   Code     RESOLVED    CLOSED
```

## 📊 Analysis Frequency

- **Daily**: Log issues as discovered
- **Weekly**: Quick scan for critical issues
- **Monthly**: Deep pattern analysis
- **Quarterly**: Create ADRs from patterns

## 💡 Pro Tips

1. **Log Immediately**: Don't wait - context evaporates quickly
2. **Be Specific**: "StateManager slow with 10+ stories" not "StateManager slow"
3. **Think Architecturally**: Is this a symptom of a deeper design issue?
4. **Cross-Reference**: Link related issues together
5. **Update Promptly**: Change status as soon as resolved
6. **Review Patterns**: Look for trends monthly

## 📖 Full Documentation

- **[Issue Log Guide](ISSUE_LOG_GUIDE.md)** - Comprehensive guide
- **[Issue Template](ISSUE_TEMPLATE.yaml)** - Copy-paste template
- **[README](README.md)** - Quality directory overview

## 🎯 Example Entry (Minimal)

```yaml
- id: "ISSUE-001"
  title: "StateManager transaction timeout with large epics"
  description: |
    When executing an epic with 10+ stories, StateManager transaction
    times out after 30 seconds, causing orchestration to fail.

  timestamp: "2025-11-11T14:32:00Z"
  reporter: "Omar"
  category: "STATE_MANAGEMENT"
  severity: "HIGH"
  type: "BUG"
  status: "OPEN"

  version: "v1.5.0"
  steps_to_reproduce:
    - "Create epic with 12 stories"
    - "Execute epic: obra epic execute 1 --project 1"
    - "Observe timeout after 6th story"

  expected_behavior: "Epic executes all stories without timeout"
  actual_behavior: "Transaction timeout after 30 seconds"

  affected_components:
    - "src/state_manager.py"
    - "src/orchestrator.py"

  tags:
    - "transaction-timeout"
    - "scalability"
```

## 🚫 What NOT to Log

- Automated test failures (covered by pytest)
- Planned features (use GitHub Issues)
- Code review findings (use PR comments)
- Security vulnerabilities (report separately)
- Issues already tracked elsewhere (duplication)

---

**Quick Help**: `python3 docs/quality/analyze_issues.py --help`

**Full Guide**: [ISSUE_LOG_GUIDE.md](ISSUE_LOG_GUIDE.md)
