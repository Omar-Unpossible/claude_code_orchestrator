# Simplified Quick Start: Real Orchestration Test

**Goal**: Run your first real Obra orchestration in 10 minutes

**No API keys needed!** Claude Code uses your existing login.

---

## ✅ Prerequisites (2 minutes)

### 1. Check Claude Code Authentication
```bash
# Are you logged in?
claude --version

# ✅ If you see version number, you're ready!
# ❌ If error, run: claude login
```

### 2. Check Ollama
```bash
# Is Ollama running?
curl http://localhost:11434/api/tags

# ✅ If you see JSON response, you're ready!
# ❌ If connection refused:
systemctl start ollama  # Linux
# or: ollama serve &     # Mac/Windows
```

### 3. Check Qwen Model
```bash
# Is Qwen downloaded?
ollama list | grep qwen

# ✅ If you see qwen2.5-coder, you're ready!
# ❌ If not found:
ollama pull qwen2.5-coder:32b  # Takes 10-20 min (20GB)
# Alternative (faster, smaller):
ollama pull qwen2.5-coder:7b   # Takes 3-5 min (4GB)
```

**That's it!** No API keys, no environment variables, no configuration files needed.

---

## 🚀 Run First Test (5 minutes)

### Simple Test: Hello World

```bash
# Navigate to Obra directory
cd /home/omarwsl/projects/claude_code_orchestrator

# Activate virtual environment
source venv/bin/activate

# Run simple test
python scripts/test_real_orchestration.py --task-type simple
```

### What You Should See

```
================================================================================
OBRA REAL ORCHESTRATION TEST
================================================================================
Task Type: simple
Max Iterations: 5
Time: 2025-11-02T...
================================================================================

Checking prerequisites...
✓ Ollama is running
✓ Claude Code CLI: 2.0.31 (Claude Code)
✓ Claude Code uses session authentication (no API key needed)
✓ Workspace directory: /tmp/obra_real_test/workspace

✅ All prerequisites met!

================================================================================
INITIALIZING ORCHESTRATOR
================================================================================
✓ Orchestrator created
Initializing components...
✓ All components initialized

================================================================================
CREATING PROJECT AND TASK
================================================================================
✓ Project created: ID=1, Name='Real Orchestration Test'
✓ Task created: ID=1, Title='Create Hello World'

================================================================================
EXECUTING TASK
================================================================================
Starting task execution...
(This may take several minutes)

Iteration 1/5
  → Building context...
  → Generating prompt...
  → Sending to agent...
  → Agent responded (543 chars)
  → Validating response...
  → Scoring quality... (85/100)
  → Calculating confidence... (75/100)
  → Decision: PROCEED

================================================================================
EXECUTION RESULTS
================================================================================
Status: completed
Iterations: 1
Quality Score: 85.00/100
Confidence: 75.00/100

Generated Files:
  - hello.py

✅ TEST PASSED - Task completed successfully!
```

### Check the Generated Code

```bash
# View generated file
cat /tmp/obra_real_test/workspace/hello.py

# Run it
python /tmp/obra_real_test/workspace/hello.py
# Should print: Hello, World!
```

---

## 🎯 If It Works

**Congratulations!** Obra is orchestrating Claude Code successfully! 🎉

### Try More Complex Tasks

**Calculator** (Original test project):
```bash
python scripts/test_real_orchestration.py --task-type calculator
```

Expected: Creates `calculator.py` and `test_calculator.py` with working code.

**Todo List** (Complex CLI app):
```bash
python scripts/test_real_orchestration.py --task-type complex
```

Expected: Creates complete todo list application with tests.

### What Just Happened?

1. ✅ Obra initialized all components (StateManager, LLM, Agent, etc.)
2. ✅ Created project and task in database
3. ✅ Generated optimized prompt from task description
4. ✅ Started Claude Code subprocess (using YOUR login)
5. ✅ Claude generated code
6. ✅ Validated response format
7. ✅ Scored code quality (using Ollama/Qwen)
8. ✅ Calculated confidence
9. ✅ DecisionEngine decided to proceed
10. ✅ Saved everything to database
11. ✅ Complete orchestration! 🚀

---

## ❌ If It Doesn't Work

### Common Issues

#### 1. Claude Code Not Authenticated
```
Error: Claude Code authentication failed
```

**Fix**:
```bash
claude logout
claude login
# Follow browser prompts
claude --version  # Verify
```

#### 2. Ollama Not Running
```
Error: Connection refused (localhost:11434)
```

**Fix**:
```bash
# Linux
systemctl start ollama

# Mac
brew services start ollama

# Windows/Manual
ollama serve &

# Verify
curl http://localhost:11434/api/tags
```

#### 3. Qwen Model Not Found
```
Error: model 'qwen2.5-coder:32b' not found
```

**Fix**:
```bash
# Pull the model
ollama pull qwen2.5-coder:32b

# Or use smaller version
ollama pull qwen2.5-coder:7b

# Update config to use smaller model if needed
```

#### 4. Agent Timeout
```
Error: Agent did not become ready in 30 seconds
```

**Fix**:
```bash
# Test Claude starts
claude --version
echo "test" | timeout 10 claude

# If slow, increase timeout:
# Edit config/real_agent_config.yaml
# Change: timeout_ready: 60  (from 30)
```

#### 5. Quality/Confidence Too Low
```
Status: escalated
Reason: Quality score below threshold
```

**Not an error!** This is the safety system working. The task was:
- Ambiguous, or
- Claude's response was incomplete, or
- Code quality was poor

**This is a feature**, not a bug. It means Obra correctly identified an issue and triggered a breakpoint for human review.

---

## 📊 Understanding the Output

### Execution Log

```
Iteration 1/5
  → Building context...          # ContextManager
  → Generating prompt...          # PromptGenerator
  → Sending to agent...           # ClaudeCodeLocalAgent
  → Agent responded (543 chars)   # Response received
  → Validating response...        # ResponseValidator
  → Scoring quality... (85/100)   # QualityController + Ollama
  → Calculating confidence... (75) # ConfidenceScorer
  → Decision: PROCEED             # DecisionEngine
```

Each line shows a different component of the orchestration pipeline.

### Status Types

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `completed` | ✅ Task finished successfully | Celebrate! |
| `escalated` | ⚠️ Needs human review | Check reason, may need to refine task |
| `failed` | ❌ Error occurred | Check logs, debug |

### Scores

**Quality Score** (0-100):
- Scored by QualityController using Ollama/Qwen
- Checks: syntax, structure, completeness
- Threshold: 70 (configurable)

**Confidence Score** (0-100):
- Calculated by ConfidenceScorer
- Weighs: validation, quality, agent health, retries
- Threshold: 50 (configurable)

---

## 🎓 Next Steps

### Explore Features

**Monitor in Real-Time**:
```bash
# Terminal 1: Run test
python scripts/test_real_orchestration.py --task-type calculator

# Terminal 2: Watch logs
tail -f logs/real_agent_test.log

# Terminal 3: Watch workspace
watch -n 1 'ls -lt /tmp/obra_real_test/workspace/'
```

**Test Breakpoints**:
```python
# Create ambiguous task (will trigger breakpoint)
task = {
    'title': 'Improve the code',
    'description': 'Make it better'  # Too vague!
}

# Expected: Status = escalated, Reason = Low quality/confidence
```

**Test Multi-Iteration**:
```bash
# Complex task that needs multiple iterations
python scripts/test_real_orchestration.py --task-type complex --max-iterations 10
```

### Read Full Documentation

- **Authentication**: `docs/development/AUTHENTICATION_MODEL.md`
- **Complete Plan**: `docs/development/REAL_ORCHESTRATION_READINESS_PLAN.md`
- **Readiness Summary**: `docs/development/READINESS_SUMMARY.md`

---

## 📝 What's Different from Mock Test?

| Aspect | Mock Test | Real Test |
|--------|-----------|-----------|
| Agent | MockAgent (fake) | ClaudeCodeLocalAgent (real) |
| Code Generation | Hardcoded | Claude generates |
| Validation | Skipped | Real validation |
| Quality Score | Hardcoded (85) | Ollama calculates |
| Confidence | Hardcoded (75) | Real calculation |
| Prompts | Not generated | PromptGenerator |
| Decisions | Not made | DecisionEngine |
| **Orchestration** | ❌ Not tested | ✅ REAL! |

---

## 🏁 Success Criteria

You're successful when:
- [ ] Test runs without errors
- [ ] Status shows `completed`
- [ ] Files generated in `/tmp/obra_real_test/workspace/`
- [ ] Generated code actually works
- [ ] Quality score > 70
- [ ] Confidence score > 50

**If all checked**: Obra is working! 🎉

---

## 💡 Key Takeaways

1. **No API Key Needed**: Claude Code uses your existing login
2. **Subprocess Inheritance**: Obra runs `claude` with your credentials
3. **Full Orchestration**: All components working together
4. **Real LLM Validation**: Ollama/Qwen scores quality
5. **Safety System**: Breakpoints trigger on low quality/confidence
6. **Production Ready**: This is the real deal!

---

**Time to First Success**: 10-15 minutes
**Prerequisites**: Claude login + Ollama + Qwen model
**Difficulty**: Easy (if prerequisites met)
**Result**: Working autonomous orchestration! 🚀
