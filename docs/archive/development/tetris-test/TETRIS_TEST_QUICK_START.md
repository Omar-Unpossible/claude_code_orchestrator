# Tetris Game Test - Quick Start Guide

**Test Plan**: See `TETRIS_GAME_TEST_PLAN.md` for full details

---

## ✅ Pre-Flight Checklist (COMPLETE)

- ✅ **Godot 4.5.1** installed and working
- ✅ **Headless mode** verified (`godot --headless --version`)
- ✅ **Target directory** clean (`/projects/test_tetrisgame` doesn't exist)
- ✅ **Obra configured** with simplified decision logic (Nov 2025 update)
- ✅ **Test plan documented** at `docs/development/TETRIS_GAME_TEST_PLAN.md`
- ✅ **LLM configured** - Choose Ollama or OpenAI Codex (see below)

---

## ⚙️ LLM Configuration (Choose One)

**IMPORTANT**: Obra now supports **flexible LLM orchestration**. Choose the LLM that best fits your setup:

### Option A: Ollama (Qwen) - Local GPU ⚡

**Best For**: Users with high-end GPU (RTX 5090 or similar)

**Requirements**:
- GPU with 32GB+ VRAM
- Ollama installed and running
- Qwen 2.5 Coder 32B model downloaded

**Configuration** (`config/config.yaml`):
```yaml
llm:
  type: ollama
  model: qwen2.5-coder:32b
  base_url: http://172.29.144.1:11434
  endpoint: http://172.29.144.1:11434
```

**Verify Setup**:
```bash
# Check Ollama is running
curl http://172.29.144.1:11434/api/tags

# Should return model list including qwen2.5-coder:32b
```

**Pros**:
- ⚡ Fastest (1-3s per validation)
- 💰 Free (after hardware cost)
- 🔒 Fully local (no network required)
- 🎯 High reliability (100% uptime)

**Cons**:
- 💻 Requires expensive GPU ($2000+)
- ⏱️ 4-8 hours setup time (first time)

---

### Option B: OpenAI Codex - Subscription 🌐

**Best For**: Users without GPU, quick testing, or subscription-based deployment

**Requirements**:
- OpenAI Codex CLI installed
- Active OpenAI subscription ($20/mo)
- Internet connection

**Configuration** (`config/config.yaml`):
```yaml
llm:
  type: openai-codex
  model: codex-mini-latest
  codex_command: codex
  timeout: 60
```

**Verify Setup**:
```bash
# Check Codex CLI is installed
which codex
# Should return: /usr/local/bin/codex (or similar)

# Check version
codex --version
# Should show version info
```

**Pros**:
- 🚀 Quick setup (5 minutes)
- 💸 Low upfront cost ($0)
- 🌐 No hardware requirements
- 📱 Works anywhere with internet

**Cons**:
- 🐌 Slower (2-5s per validation, network overhead)
- 💳 Monthly subscription ($20/mo)
- 📡 Requires internet connection
- ⚠️ Rate limiting possible

---

### Which Should You Choose?

| Scenario | Recommended LLM |
|----------|----------------|
| **Have RTX 5090 or similar** | Ollama (faster, free) |
| **No GPU or low VRAM** | OpenAI Codex (only option) |
| **Testing/Demo** | OpenAI Codex (quick setup) |
| **Production/Long-term** | Ollama (cost-effective) |
| **Offline development** | Ollama (no network needed) |
| **Quick validation** | OpenAI Codex (minimal setup) |

**Note**: Both LLMs are **equally capable** of orchestrating the Tetris game. The choice is purely based on your hardware, budget, and deployment model.

---

## 🚀 Quick Start - Copy/Paste Commands

### Step 1: Create Obra Project

```bash
cd /home/omarwsl/projects/claude_code_orchestrator
./venv/bin/python -m src.cli project create "Tetris Game Development Test"
```

**Note the PROJECT_ID returned** (e.g., `Project ID: 2`)

---

### Step 2: Create Planning Task

Replace `<PROJECT_ID>` with the actual ID from Step 1:

```bash
./venv/bin/python -m src.cli task create \
  --project <PROJECT_ID> \
  --title "Tetris Game - Milestone Planning" \
  --description "Create a Tetris clone game using the Godot 4.5 game engine. The project should be located at /projects/test_tetrisgame/.

REQUIREMENTS:
1. Develop the game entirely in headless mode (no GUI tools - file creation and CLI only)
2. The game must include:
   - Title screen with \"Play Now\" button
   - Main game scene with Tetris gameplay (falling blocks, rotation, translation via keyboard, row clearing, scoring)
   - Game over detection and score display
   - \"Play Again?\" functionality to restart
3. Use minimal graphics (simple ColorRect nodes are acceptable - no polished sprites needed)
4. Implement unit tests for core game logic (rotation, collision detection, line clearing, scoring)
5. Generate all necessary project documentation (README, design docs, etc.)

FIRST TASK:
Break this project down into logical milestones with clear deliverables for each milestone. Create a development plan that can be executed iteratively across multiple work sessions.

For each milestone, specify:
- Milestone name and number
- Deliverables (files, features, tests)
- Success criteria
- Dependencies on previous milestones

After creating the milestone plan, we will execute each milestone as a separate task." \
  --task-type planning
```

**Note the TASK_ID returned** (e.g., `Task ID: 1`)

---

### Step 3: Execute Planning Task

Replace `<TASK_ID>` with the actual ID from Step 2:

```bash
# Execute with LLM configured in config.yaml (default)
./venv/bin/python -m src.cli task execute <TASK_ID>
```

**LLM Selection Note**: The LLM type is determined by `config/config.yaml`. Ensure you've configured your preferred LLM (Ollama or OpenAI Codex) before executing.

**Verify which LLM will be used**:
```bash
# Check your current LLM configuration
grep -A 3 "^llm:" config/config.yaml
```

**Expected output** (Ollama example):
```yaml
llm:
  type: ollama
  model: qwen2.5-coder:32b
  base_url: http://172.29.144.1:11434
```

**Expected output** (Codex example):
```yaml
llm:
  type: openai-codex
  model: codex-mini-latest
  codex_command: codex
```

**Wait for completion**, then review the generated milestone plan.

**During execution**, you'll see log messages indicating which LLM is being used:
- Ollama: `[LLM:ollama] Validating response...`
- Codex: `[LLM:openai-codex] Validating response...`

---

### Step 4: Execute Each Milestone

For each milestone from the plan, create and execute a task:

```bash
# Example: Milestone 1
./venv/bin/python -m src.cli task create \
  --project <PROJECT_ID> \
  --title "Tetris - Milestone 1: <milestone_name>" \
  --description "Implement Milestone 1: <milestone_name>

DELIVERABLES:
<list from milestone plan>

CONSTRAINTS:
- Headless development only (use file creation/editing and CLI commands)
- Test all logic with unit tests
- Document your work (code comments, update README)

VALIDATION:
- Run godot --headless to check for errors
- Ensure unit tests pass
- Verify scene files load correctly" \
  --task-type code_generation

# Execute the milestone (uses LLM from config.yaml)
./venv/bin/python -m src.cli task execute <MILESTONE_TASK_ID>
```

**Repeat** for each milestone until project is complete.

**Note**: All milestones will use the same LLM configured in `config.yaml`. If you want to test with a different LLM, update the configuration before executing the next milestone.

---

## 📊 Monitoring Progress

### Check Task Status

```bash
./venv/bin/python -m src.cli task status <TASK_ID>
```

### View Project Tasks

```bash
./venv/bin/python -m src.cli project tasks <PROJECT_ID>
```

### Watch Logs

```bash
tail -f logs/orchestrator.log
```

### Check Project Files

```bash
ls -la /projects/test_tetrisgame/
tree /projects/test_tetrisgame/
```

---

## ✅ Validation Commands

### Run Headless Test

```bash
godot --headless --path /projects/test_tetrisgame --quit
```

### Check for Errors

```bash
# Should exit without errors
echo $?  # 0 = success
```

### Review Generated Files

```bash
# Project structure
tree /projects/test_tetrisgame/

# Documentation
cat /projects/test_tetrisgame/README.md

# Source files
ls -la /projects/test_tetrisgame/scripts/
```

### (Optional) Visual Playthrough

**After test completion**, if desired:

```bash
godot --path /projects/test_tetrisgame
```

---

## 📈 Success Criteria

**Minimum Success**:
- ✅ Project runs without crashes
- ✅ Core game logic tests pass
- ✅ All scenes load successfully
- ✅ Documentation generated

**Full Success**:
- ✅ All minimum criteria
- ✅ Game is playable (manual verification)
- ✅ Comprehensive tests (>80% coverage)
- ✅ Complete documentation

---

## 🔧 Troubleshooting

### If Obra Gets Stuck

**Check decision logs:**
```bash
grep "Decision:" logs/orchestrator.log | tail -20
```

**Check quality scores:**
```bash
grep "Quality:" logs/orchestrator.log | tail -20
```

### If Task Hits Max Turns

**Normal behavior**: Obra will retry with 2x max_turns (auto-retry enabled)

**If retry exhausted**:
- Review the task output
- Create a new task with more focused scope
- Adjust the prompt based on what worked/failed

### If Godot Errors

**Check Godot logs:**
```bash
cat /projects/test_tetrisgame/.godot/logs/*
```

**Validate project file:**
```bash
godot --headless --check-only --path /projects/test_tetrisgame
```

---

### LLM-Specific Issues

#### Ollama Not Responding

**Problem**: `ConnectionError: Failed to connect to Ollama`

**Solution**:
1. Verify Ollama is running:
   ```bash
   curl http://172.29.144.1:11434/api/tags
   ```
2. If not running, start Ollama:
   ```bash
   systemctl start ollama  # Linux
   # or check your Ollama installation docs
   ```
3. Check model is loaded:
   ```bash
   curl http://172.29.144.1:11434/api/show -d '{"name": "qwen2.5-coder:32b"}'
   ```

#### OpenAI Codex CLI Not Found

**Problem**: `PluginNotFoundError: LLM type 'openai-codex' not found` or `FileNotFoundError: codex command not found`

**Solution**:
1. Verify Codex CLI is installed:
   ```bash
   which codex
   ```
2. If not found, install Codex:
   ```bash
   # Follow OpenAI Codex CLI installation instructions
   npm install -g @openai/codex-cli
   ```
3. Update config with full path:
   ```yaml
   llm:
     type: openai-codex
     codex_command: /usr/local/bin/codex  # Use output from 'which codex'
   ```

#### Codex Rate Limiting

**Problem**: `Rate limit exceeded` errors during execution

**Solution**:
1. Check your OpenAI subscription status
2. Obra automatically adds delays between prompts (5s default)
3. If still hitting limits, you can:
   - Wait 1 minute before retrying
   - Switch to Ollama (no rate limits)
   - Upgrade your OpenAI plan

#### Network Errors (Codex Only)

**Problem**: `Connection timeout` or `Network unreachable`

**Solution**:
1. Check internet connectivity:
   ```bash
   ping openai.com
   ```
2. Increase timeout in config:
   ```yaml
   llm:
     type: openai-codex
     timeout: 120  # Increase from 60 to 120 seconds
   ```
3. For offline development, switch to Ollama

#### Different Results Between LLMs

**Problem**: Test succeeds with Ollama but fails with Codex (or vice versa)

**Symptoms**:
- Different quality scores for same Claude response
- One LLM gets stuck in clarification loops
- Different decision patterns (PROCEED vs CLARIFY)

**Solution**:
1. Compare quality scores in logs:
   ```bash
   # Ollama run
   grep "Quality:" logs/orchestrator_ollama.log | awk '{print $NF}' | awk '{s+=$1; n++} END {print "Average:", s/n}'

   # Codex run
   grep "Quality:" logs/orchestrator_codex.log | awk '{print $NF}' | awk '{s+=$1; n++} END {print "Average:", s/n}'
   ```
2. Check decision distribution:
   ```bash
   grep "Decision:" logs/orchestrator.log | cut -d: -f3 | sort | uniq -c
   ```
3. If quality scores differ by >20%, this may indicate:
   - Prompt sensitivity (Claude response varies slightly)
   - LLM reasoning differences (expected)
   - Bug in one LLM interface (report if consistent)

**Note**: Both LLMs should produce similar overall results. If one consistently fails while the other succeeds, report this as a bug.

---

## 📁 Test Artifacts Location

- **Test Plan**: `docs/development/TETRIS_GAME_TEST_PLAN.md`
- **Obra Logs**: `logs/orchestrator.log`
- **Obra Database**: `data/orchestrator.db`
- **Project Files**: `/projects/test_tetrisgame/`
- **Test Results**: To be added to `docs/development/phase-reports/`

---

## 🎯 Next Actions

1. ✅ Run Step 1: Create Obra project
2. ✅ Run Step 2: Create planning task
3. ✅ Run Step 3: Execute planning
4. ⏳ Review milestone plan
5. ⏳ Execute milestones sequentially
6. ⏳ Validate final project
7. ⏳ Document lessons learned

---

**Status**: Ready to Execute
**Last Updated**: 2025-11-05
