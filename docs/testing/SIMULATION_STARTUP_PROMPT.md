# Obra Simulation Test - Startup Prompt for Claude Code

**Instructions**: Copy the text below and paste it into a fresh Claude Code session to run the Obra simulation test autonomously.

---

## Startup Prompt

```
Hello! I need your help running a comprehensive end-to-end test of the Obra orchestration system.

CONTEXT:
You are testing Obra v1.8.0, a hybrid AI orchestration platform that combines local LLM reasoning with remote code generation (Claude Code CLI). Your mission is to build a JSON-to-Markdown CLI tool using Obra's natural language interface and validate the full development workflow.

OBJECTIVE:
Build a working CLI tool called "json2md" that converts JSON data to formatted Markdown reports, with full testing and documentation. Use Obra's orchestration to manage the workflow, and analyze production logs to debug issues.

MISSION:
1. Create project and epic/story hierarchy via natural language commands
2. Execute each story to implement the tool
3. Add comprehensive tests (≥80% coverage)
4. Debug using production logs
5. Finalize documentation
6. Validate success criteria and generate report

DELIVERABLES:
- Working CLI tool with argument parsing
- JSON loading and Markdown generation
- Unit and integration tests (≥80% coverage)
- README with usage examples
- Production log analysis
- Validation report

TIMELINE: ~90 minutes

DETAILED INSTRUCTIONS:
Read and follow the complete simulation guide at:
/home/omarwsl/projects/claude_code_orchestrator/docs/testing/OBRA_SIMULATION_TEST.md

QUICK REFERENCE:
Use the quick start guide for commands:
/home/omarwsl/projects/claude_code_orchestrator/docs/testing/OBRA_SIMULATION_QUICKSTART.md

STARTING POINT:
1. First, read OBRA_SIMULATION_TEST.md to understand the full test plan
2. Then, start Obra interactive mode:
   cd /home/omarwsl/projects/claude_code_orchestrator
   ./scripts/startup/obra.sh
3. Follow Phase 1-5 instructions from the simulation guide
4. Use production logs to debug issues
5. Generate final validation report

SUCCESS CRITERIA:
✅ Working CLI tool (manual test passes)
✅ All tests pass (pytest)
✅ Coverage ≥80%
✅ README exists
✅ Production logs show quality ≥0.7
✅ Epic marked complete

IMPORTANT REMINDERS:
- Use natural language (no slash prefix) to send commands to Obra
- Use /to-impl to send messages directly to the implementer
- Use /status to check current progress
- Monitor production logs at ~/obra-runtime/logs/production.jsonl
- If stuck, use /pause and /stop to investigate
- Generate validation report at the end

Please begin by reading the full simulation guide, then start the test. Report your progress at each phase and any issues you encounter.
```

---

## Expected Response Flow

**Phase 1** (Setup):
```
Claude: I've read the simulation guide. Starting Phase 1: Setup and Planning.

Claude: [Starts Obra interactive mode]

Claude: [Executes NL commands to create project/epic/stories]

Claude: Successfully created:
- Project: "JSON to Markdown Converter"
- Epic 1: "JSON-to-Markdown CLI Tool"
- Stories 1-7: [lists stories]

Phase 1 complete. Production log shows:
- 8 successful entity creations
- Average confidence: 0.92
- No errors

Proceeding to Phase 2...
```

**Phase 2-4** (Implementation and Testing):
```
Claude: Executing Story 1 (CLI argument parsing)...

Claude: Story 1 complete. Quality score: 0.85. Tests: 3/3 passing.

Claude: Executing Story 2 (JSON loading)...

Claude: Story 2 complete. Quality score: 0.78. Found edge case issue - creating fix task.

Claude: [Creates and executes bug fix task]

Claude: Bug fix complete. Re-running tests... All passing.

[Continues for all stories...]
```

**Phase 5** (Validation):
```
Claude: All stories complete. Running final validation...

Claude: ✅ CLI tool works (tested with sample JSON)
Claude: ✅ Tests pass (12/12 passing)
Claude: ✅ Coverage: 87%
Claude: ✅ README exists with examples
Claude: ✅ Production log quality: 0.83 average

Claude: Generating validation report...

[Shows report with metrics]

Claude: Simulation test SUCCESSFUL. All P0 criteria met, 2/3 P1 criteria met.

Issues discovered:
1. [List any Obra bugs found]
2. [List any UX improvements needed]

Lessons learned:
- [What worked well]
- [What could improve]
- [Performance observations]

Total duration: 85 minutes
```

---

## Adaptive Instructions

**If Claude asks questions:**

Q: "Where should I create the json2md project files?"
A: "Create them in a new directory: /home/omarwsl/projects/json2md"

Q: "Should I enable git auto-commit?"
A: "Yes, enable git integration to test that feature"

Q: "What if a story fails quality validation?"
A: "Create a fix task and iterate. Production logs will show the quality issues."

Q: "How much detail should I provide in progress updates?"
A: "Brief updates after each story, detailed report at end"

**If Claude gets stuck:**

Issue: "NL command not recognized"
Help: "Check LLM connection: python -m src.cli llm status"

Issue: "Quality scores consistently low"
Help: "Use /to-impl to send explicit improvement requests to Claude Code"

Issue: "Obra hangs or crashes"
Help: "Use /stop to exit, check logs, restart and resume from last checkpoint"

Issue: "Tests fail repeatedly"
Help: "Create dedicated debugging task with specific test failure details"

---

## Post-Simulation Questions

After completing the simulation, answer these:

1. **Did the simulation achieve all P0 success criteria?** (Yes/No + details)

2. **What was the average quality score? Confidence?** (Extract from logs)

3. **How many iterations per story?** (Count retries/fixes)

4. **Were there any Obra bugs discovered?** (List with severity)

5. **Was the NL interface intuitive?** (UX feedback)

6. **Did production logs help with debugging?** (Effectiveness rating 1-10)

7. **Would this be faster with Obra vs direct Claude usage?** (Compare and justify)

8. **What would you improve in Obra?** (Top 3 suggestions)

---

## Alternative Startup Command

If `obra.sh` doesn't work:

```bash
cd /home/omarwsl/projects/claude_code_orchestrator
python -m src.cli interactive
```

If LLM connection fails:

```bash
# Check LLM status
python -m src.cli llm status

# Reconnect
python -m src.cli llm reconnect

# Or manually start Ollama (if on host)
# In separate terminal on host machine:
ollama serve
```

---

## Success Metrics Template

Use this template for final report:

```markdown
# Obra Simulation Test Results

**Date**: [YYYY-MM-DD]
**Duration**: [X minutes]
**Obra Version**: v1.8.0

## Outcomes
- [ ] CLI tool works
- [ ] Tests pass (X/Y passing)
- [ ] Coverage: X%
- [ ] README complete
- [ ] Quality ≥0.7
- [ ] Epic complete

## Metrics
- Tasks created: X
- Tasks succeeded: X
- Tasks failed: X
- Average quality: X.XX
- Average confidence: X.XX
- Average duration: X.XX seconds
- Total errors: X

## Issues Found
1. [Issue description + severity]
2. ...

## UX Observations
- What was intuitive
- What was confusing
- Suggestions for improvement

## Value Assessment
- Faster than direct Claude? [Yes/No + X% faster]
- Better quality? [Yes/No + reasoning]
- Would use in production? [Yes/No + why]

## Recommendations
1. [Top improvement]
2. [Second improvement]
3. [Third improvement]
```

---

**Good luck! Report your findings when complete.**
