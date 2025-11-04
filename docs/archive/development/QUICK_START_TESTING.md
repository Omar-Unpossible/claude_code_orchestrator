# Quick Start: Real-World Testing

**Ready to test Obra in 5 minutes?** Follow this guide to run your first end-to-end test.

## Prerequisites Check (1 minute)

```bash
# 1. Check Python version (need 3.12+)
python --version

# 2. Check virtual environment
which python  # Should show venv/bin/python

# 3. Check Claude Code CLI (optional, can use mock)
claude --version  # or: npx @anthropics/claude-code --version

# 4. Check Ollama (optional, can skip LLM validation)
curl -s http://localhost:11434/api/tags | grep qwen

# 5. Set API key (if using real Claude Code)
export ANTHROPIC_API_KEY=your_key_here
```

## Quick Test Run (2 minutes)

Run the simplest test scenario to verify everything works:

```bash
# Navigate to project directory
cd /home/omarwsl/projects/claude_code_orchestrator

# Activate virtual environment
source venv/bin/activate

# Run Scenario 1 (Happy Path) with mock agent
python tests/test_runthrough.py --scenario 1

# Expected output:
# ================================================================================
# OBRA REAL-WORLD RUNTHROUGH TEST
# ================================================================================
#
# 1. Creating test directories...
#    ✓ Test directory: /tmp/obra_test_run
#    ✓ Workspace: /tmp/obra_test_run/workspace
# ...
# ================================================================================
# SCENARIO 1: PASSED
# ================================================================================
```

**That's it!** If you see `SCENARIO 1: PASSED`, the system is working correctly.

## What Just Happened?

The test script:
1. ✅ Created a test project and task
2. ✅ Simulated agent execution (generated calculator code)
3. ✅ Created actual Python files in workspace
4. ✅ Ran pytest to validate the code
5. ✅ Calculated quality and confidence scores
6. ✅ Persisted all state to database
7. ✅ Generated a test report

## View Results

```bash
# Check generated files
ls -la /tmp/obra_test_run/workspace/

# View calculator code
cat /tmp/obra_test_run/workspace/calculator.py

# View test code
cat /tmp/obra_test_run/workspace/test_calculator.py

# Run tests manually
cd /tmp/obra_test_run/workspace
python -m pytest test_calculator.py -v

# View test report
cat /tmp/obra_test_run/test_report.json | jq .

# Check database
sqlite3 data/orchestrator_test.db "SELECT * FROM tasks;"
```

## Run All Scenarios (15 minutes)

To run the complete test suite:

```bash
python tests/test_runthrough.py --all
```

This will execute:
- ✅ Scenario 1: Happy Path (5 min)
- ✅ Scenario 2: Quality Control (5 min)
- ⏳ Scenario 3-6: Coming soon!

## Using Real Claude Code CLI

To test with the actual Claude Code agent (not mock):

```bash
# 1. Ensure Claude Code is installed
npm install -g @anthropics/claude-code

# 2. Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Edit test config to use real agent
# Change agent.type from 'mock' to 'claude_code_local'
# The test script does this automatically if you use:

python tests/test_runthrough.py --scenario 1 --use-real-agent
```

**Note**: Real agent tests take longer (10-15 minutes) and use your Anthropic API credits.

## Troubleshooting

### Test fails with "pytest not found"

```bash
pip install pytest
```

### Test fails with "No module named 'src'"

```bash
# Make sure you're in the project root
cd /home/omarwsl/projects/claude_code_orchestrator

# Ensure PYTHONPATH is set
export PYTHONPATH=/home/omarwsl/projects/claude_code_orchestrator:$PYTHONPATH
```

### Database locked error

```bash
# Close other connections and retry
rm data/orchestrator_test.db
python tests/test_runthrough.py --scenario 1
```

### Permission denied on workspace

```bash
rm -rf /tmp/obra_test_run
mkdir -p /tmp/obra_test_run/workspace
chmod 755 /tmp/obra_test_run/workspace
```

## Clean Up

Remove all test data and start fresh:

```bash
python tests/test_runthrough.py --clean
```

## Next Steps

### If Tests Pass ✅

1. **Try with Real Agent**: Use `claude_code_local` instead of mock
2. **Run Full Suite**: Execute all scenarios with `--all`
3. **Create Custom Tasks**: Edit test script to add your own scenarios
4. **Production Setup**: Follow `COMPLETE_SETUP_WALKTHROUGH.md`

### If Tests Fail ❌

1. **Check Logs**: Review `logs/test_runthrough.log`
2. **Verify Setup**: Re-run prerequisites check above
3. **Debug Mode**: Set `logging.level: DEBUG` in config
4. **Get Help**: Check `docs/troubleshooting/` or create GitHub issue

## Understanding Test Output

### Test Report

```json
{
  "summary": {
    "total_scenarios": 1,
    "passed": 1,
    "failed": 0,
    "success_rate": 100.0,
    "total_duration": 45.2
  },
  "scenarios": [
    {
      "scenario_id": 1,
      "status": "PASSED",
      "validations": {
        "project_created": true,
        "task_created": true,
        "files_created": true,
        "tests_passed": true,
        "quality_threshold": true,
        "confidence_threshold": true,
        "task_completed": true,
        "state_persisted": true
      },
      "metrics": {
        "quality_score": 85,
        "confidence_score": 75
      }
    }
  ]
}
```

### Success Criteria

For Scenario 1 to pass, ALL must be true:
- ✅ `project_created`: Project in database
- ✅ `task_created`: Task in database
- ✅ `files_created`: calculator.py and test_calculator.py exist
- ✅ `tests_passed`: pytest runs successfully (5 tests pass)
- ✅ `quality_threshold`: Quality score ≥ 70
- ✅ `confidence_threshold`: Confidence score ≥ 50
- ✅ `task_completed`: Task status = COMPLETED
- ✅ `state_persisted`: Database has correct state

## Advanced Usage

### Run Specific Steps

```python
# Python REPL
from tests.test_runthrough import RunthroughTester

tester = RunthroughTester()
tester.setup()
result = tester.run_scenario_1()
print(f"Status: {result.status}")
print(f"Validations: {result.validations}")
tester.teardown()
```

### Custom Scenarios

Copy `test_runthrough.py` and add your own scenarios:

```python
def run_scenario_custom(self) -> TestResult:
    """My custom test scenario."""
    # Your test logic here
    pass
```

### Integration with CI/CD

```yaml
# .github/workflows/test.yml
- name: Run end-to-end tests
  run: |
    source venv/bin/activate
    python tests/test_runthrough.py --all
```

## FAQ

**Q: How long do tests take?**
A: Scenario 1 (mock): ~2 minutes. Full suite (mock): ~15 minutes. With real agent: 30-60 minutes.

**Q: Do I need Ollama running?**
A: No, tests will skip LLM validation if Ollama isn't available. But it's recommended for full testing.

**Q: Do tests use my API credits?**
A: Only if you use `claude_code_local` agent. Mock agent doesn't call Claude API.

**Q: Can I run tests on Windows?**
A: Yes, but paths may need adjustment. WSL2 recommended.

**Q: Why does Scenario 1 create a calculator?**
A: It's a simple, testable project that validates all system components without being too complex.

**Q: How do I add more test scenarios?**
A: Edit `test_runthrough.py` and add `run_scenario_X()` methods following existing patterns.

---

**Quick Start Complete!** You're now ready to test Obra end-to-end.

For detailed test scenarios, see: `docs/development/REAL_WORLD_TEST_PLAN.md`
