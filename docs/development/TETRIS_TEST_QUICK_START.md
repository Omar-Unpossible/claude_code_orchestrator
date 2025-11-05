# Tetris Game Test - Quick Start Guide

**Test Plan**: See `TETRIS_GAME_TEST_PLAN.md` for full details

---

## ✅ Pre-Flight Checklist (COMPLETE)

- ✅ **Godot 4.5.1** installed and working
- ✅ **Headless mode** verified (`godot --headless --version`)
- ✅ **Target directory** clean (`/projects/test_tetrisgame` doesn't exist)
- ✅ **Obra configured** with simplified decision logic (Nov 2025 update)
- ✅ **Test plan documented** at `docs/development/TETRIS_GAME_TEST_PLAN.md`

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
./venv/bin/python -m src.cli task execute <TASK_ID>
```

**Wait for completion**, then review the generated milestone plan.

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

# Execute the milestone
./venv/bin/python -m src.cli task execute <MILESTONE_TASK_ID>
```

**Repeat** for each milestone until project is complete.

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
