# Obra Simulation Test - Quick Start Guide

**Mission**: Build a JSON-to-Markdown CLI tool using Obra orchestration

**Success**: Working CLI + Tests (≥80% coverage) + Documentation

**Duration**: ~90 minutes

---

## Quick Commands Reference

### Startup
```bash
cd /home/omarwsl/projects/claude_code_orchestrator
./scripts/startup/obra.sh
```

### Phase 1: Setup (10 min)
```
Create a new project called "JSON to Markdown Converter"
Create an epic for building a JSON-to-Markdown CLI tool with full testing
Create a story for CLI argument parsing in epic 1
Create a story for JSON loading and validation in epic 1
Create a story for Markdown generation in epic 1
Create a story for error handling in epic 1
Create a story for unit tests in epic 1
Create a story for integration tests in epic 1
Create a story for documentation in epic 1
Show me all stories for epic 1
```

### Phase 2-4: Execute (60 min)
```
Execute story 1
# Review output, check quality

Execute story 2
# Continue for all stories...

# If quality low or tests fail:
Create a task to fix [specific issue]
Execute task [ID]

# Check status anytime:
Show me the status of epic 1
/status
```

### Phase 5: Validate (20 min)
```
# Inside Obra, send to implementer:
/to-impl run the CLI tool with test inputs
/to-impl run pytest --cov

# Check production logs:
/stop

tail -n 50 ~/obra-runtime/logs/production.jsonl | jq 'select(.quality_score != null) | {task: .task_id, quality: .quality_score, confidence: .confidence}'

# Generate report:
pytest -v > simulation_report.txt
pytest --cov=json2md --cov-report=term >> simulation_report.txt
```

---

## Success Checklist

- [ ] Project created
- [ ] Epic created with 7+ stories
- [ ] All stories executed
- [ ] CLI tool works (manual test)
- [ ] Tests pass (pytest)
- [ ] Coverage ≥80%
- [ ] README exists
- [ ] Production logs show quality ≥0.7
- [ ] Epic marked complete

---

## Debugging Quick Reference

**NL command not working?**
```bash
python -m src.cli llm status  # Check LLM connection
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.event_type=="nl_result")' | tail -5
```

**Low quality scores?**
```
/to-impl Please improve the code based on validation feedback
# or
Create a task to refactor [module] for better quality
```

**Obra stuck?**
```
/pause
/status
/stop  # Then restart
```

**Tests failing?**
```
Create a story for fixing test failures in epic 1
Execute story [ID]
```

---

## Expected File Structure

At completion:
```
json2md/
├── json2md/
│   ├── __init__.py
│   ├── cli.py          # Argument parsing
│   ├── parser.py       # JSON loading
│   ├── generator.py    # Markdown generation
│   └── templates/
│       ├── simple.md.j2
│       └── detailed.md.j2
├── tests/
│   ├── test_cli.py
│   ├── test_parser.py
│   ├── test_generator.py
│   └── fixtures/
│       └── test_data.json
├── README.md
├── requirements.txt
└── setup.py
```

---

## Production Log Events to Monitor

**Good signs** ✅:
```json
{"event_type": "nl_result", "confidence": 0.95, "validation_status": "valid"}
{"event_type": "execution_result", "outcome": "success", "quality_score": 0.85}
```

**Warning signs** ⚠️:
```json
{"event_type": "nl_result", "confidence": 0.65}
{"event_type": "execution_result", "quality_score": 0.55}
```

**Problem signs** ❌:
```json
{"event_type": "error", "stage": "validation"}
{"event_type": "nl_result", "validation_status": "invalid"}
```

---

## Time Checkpoints

- **10 min**: Project + Epic + Stories created
- **40 min**: Stories 1-4 executed (core CLI)
- **60 min**: Stories 5-6 executed (tests)
- **80 min**: Story 7 executed (documentation)
- **90 min**: Validation complete, report generated

**If behind schedule**: Focus on P0 criteria only, skip P1/P2

---

## Final Validation Commands

```bash
# 1. Tool works
python json2md.py --input tests/fixtures/test_data.json --template simple --output report.md
cat report.md

# 2. Tests pass
pytest -v

# 3. Coverage good
pytest --cov=json2md --cov-report=term

# 4. Quality metrics
cat ~/obra-runtime/logs/production.jsonl | jq -s '[.[] | select(.quality_score != null) | .quality_score] | add / length'
```

---

## What to Report

1. **Functionality**: Does CLI work? Do tests pass?
2. **Metrics**: Quality scores, confidence, coverage
3. **Issues**: Bugs found in Obra? UX problems?
4. **Value**: Faster with Obra vs direct Claude? Better quality?
5. **Logs**: Production log summary (event counts, errors)

---

**See Full Details**: `docs/testing/OBRA_SIMULATION_TEST.md`
