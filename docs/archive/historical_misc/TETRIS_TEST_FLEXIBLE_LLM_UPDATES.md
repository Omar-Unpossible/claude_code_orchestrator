# Tetris Game Test - Flexible LLM Architecture Updates

**Date**: November 5, 2025
**Status**: Analysis Complete - Ready for Implementation
**Related Docs**:
- Original Test Plan: `docs/archive/development/tetris-test/TETRIS_GAME_TEST_PLAN.md`
- Quick Start: `docs/archive/development/tetris-test/TETRIS_TEST_QUICK_START.md`
- Flexible LLM Strategy: `docs/business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md`

---

## Executive Summary

The Tetris game development test documentation was created **before** the flexible LLM orchestrator feature (Phases 1-6) was implemented. The test currently only supports **Ollama/Qwen** as the validation LLM. With the new flexible LLM architecture, the test should be updated to validate **both Ollama and OpenAI Codex** orchestration paths.

**Key Finding**: The Tetris test is an **ideal validation** for the flexible LLM feature because it's a **long-running, multi-session orchestration** (7 milestones, 10-14 hours) that stresses the LLM interface across diverse tasks (planning, code generation, testing, documentation).

---

## What Changed: Flexible LLM Architecture

### Before (Archived Tetris Test)
```yaml
# Single LLM option hardcoded
llm:
  type: ollama
  model: qwen2.5-coder:32b
  base_url: http://172.29.144.1:11434
```

### After (Current Flexible LLM)
```yaml
# Option A: Ollama (local GPU)
llm:
  type: ollama
  model: qwen2.5-coder:32b
  base_url: http://172.29.144.1:11434

# Option B: OpenAI Codex (CLI-based, NEW)
llm:
  type: openai-codex
  model: codex-mini-latest
  codex_command: codex
  timeout: 60
```

### Key Architectural Differences

| Aspect | Ollama (Qwen) | OpenAI Codex |
|--------|---------------|--------------|
| **Interface** | HTTP API | CLI subprocess |
| **Latency** | 1-3s per prompt | 2-5s per prompt |
| **Reliability** | Local (100% uptime) | Remote (requires network) |
| **Cost** | Free (after GPU purchase) | Subscription ($20/mo) |
| **Response Format** | Streaming JSON | Non-streaming text |
| **Error Modes** | Connection refused | CLI not found, rate limiting |

---

## Analysis: Updates Required

### 1. Configuration Section (HIGH PRIORITY)

**Current State**: Docs assume Ollama only
**Required Update**: Add dual-LLM configuration instructions

**Location**: `TETRIS_TEST_QUICK_START.md` - Pre-Flight Checklist

**New Section Needed**:
```markdown
### LLM Configuration (Choose One)

#### Option A: Ollama (Qwen) - Local GPU
- **Requirements**: RTX 5090 or similar GPU, Ollama installed
- **Setup Time**: 4-8 hours (first time)
- **Cost**: Free (after hardware)
- **Reliability**: High (local)

**Configuration** (`config/config.yaml`):
```yaml
llm:
  type: ollama
  model: qwen2.5-coder:32b
  base_url: http://172.29.144.1:11434
```

**Verify**:
```bash
curl http://172.29.144.1:11434/api/tags  # Should return model list
```

#### Option B: OpenAI Codex - Subscription
- **Requirements**: OpenAI Codex CLI installed
- **Setup Time**: 5 minutes
- **Cost**: $20/mo
- **Reliability**: Medium (network-dependent)

**Configuration** (`config/config.yaml`):
```yaml
llm:
  type: openai-codex
  model: codex-mini-latest
  codex_command: codex
  timeout: 60
```

**Verify**:
```bash
which codex  # Should return path
codex --version  # Should show version
```
```

---

### 2. CLI Commands Update (HIGH PRIORITY)

**Current State**: CLI commands hardcoded for Ollama
**Required Update**: Show how to specify LLM type via CLI

**Location**: `TETRIS_TEST_QUICK_START.md` - Step 1-4

**Updates Needed**:

**Before**:
```bash
./venv/bin/python -m src.cli task execute <TASK_ID>
```

**After** (add LLM selection):
```bash
# Option A: Use Ollama (default if configured in YAML)
./venv/bin/python -m src.cli task execute <TASK_ID>

# Option B: Override to use Codex via CLI flag
./venv/bin/python -m src.cli task execute <TASK_ID> --llm-type openai-codex

# Option C: Use profile with specific LLM
./venv/bin/python -m src.cli task execute <TASK_ID> --profile codex_orchestrator
```

**New Configuration Profile** (add to `config/profiles/`):
```yaml
# config/profiles/codex_orchestrator.yaml
name: codex_orchestrator
description: Tetris test with OpenAI Codex orchestrator

llm:
  type: openai-codex
  model: codex-mini-latest
  codex_command: codex
  timeout: 60

agent:
  type: claude-code-local
  workspace_path: /projects/test_tetrisgame

# Rest of config same as default
```

---

### 3. Validation Strategy (MEDIUM PRIORITY)

**Current State**: Single LLM validation only
**Required Update**: Comparison testing between Ollama and Codex

**Location**: `TETRIS_GAME_TEST_PLAN.md` - Section 8 (Monitoring & Metrics)

**New Section Needed**:

```markdown
### Flexible LLM Comparison Testing

**Objective**: Validate that both Ollama and OpenAI Codex can successfully orchestrate the Tetris game development.

**Approach**:
1. Run complete test with Ollama (Milestone 1-7)
2. Run complete test with OpenAI Codex (Milestone 1-7)
3. Compare results across key metrics

**Metrics to Compare**:

| Metric | Ollama (Qwen) | OpenAI Codex | Notes |
|--------|---------------|--------------|-------|
| **Total iterations** | ? | ? | How many Claude prompts total |
| **Decision distribution** | ? | ? | PROCEED/CLARIFY/ESCALATE ratios |
| **Average quality score** | ? | ? | LLM validation scores |
| **Average confidence** | ? | ? | Confidence scorer output |
| **Time per milestone** | ? | ? | Wall-clock time |
| **Errors encountered** | ? | ? | Syntax, API, logic errors |
| **Final outcome** | ? | ? | Success/partial/failure |

**Expected Differences**:
- **Latency**: Codex may be 50-100% slower (network overhead)
- **Quality Scores**: May differ slightly (different LLM reasoning)
- **Error Recovery**: Both should handle errors equally well
- **Final Outcome**: **Both should successfully complete the game**

**Acceptance Criteria**:
✅ Both LLM types complete at least 5/7 milestones
✅ Core game logic works with both (unit tests pass)
✅ No catastrophic failures (crashes, infinite loops)
✅ Documentation generated by both
```

---

### 4. Test Execution Modes (MEDIUM PRIORITY)

**Current State**: Single test execution path
**Required Update**: Three test execution modes

**Location**: `TETRIS_TEST_QUICK_START.md` - New section after Step 4

**New Section**:

```markdown
## Test Execution Modes

### Mode 1: Ollama Only (Baseline)
**Use Case**: Validate local GPU orchestration

```bash
# Ensure Ollama configured in config.yaml
./venv/bin/python -m src.cli task execute <TASK_ID>
```

**Expected Time**: 10-14 hours
**Best For**: Testing with high-performance local LLM

---

### Mode 2: Codex Only (Subscription)
**Use Case**: Validate remote CLI orchestration

```bash
# Override to use Codex
./venv/bin/python -m src.cli task execute <TASK_ID> --llm-type openai-codex
```

**Expected Time**: 15-20 hours (slower due to network)
**Best For**: Testing subscription deployment model

---

### Mode 3: Comparative (Both LLMs)
**Use Case**: A/B testing to validate flexible architecture

**Run twice with different configs:**

```bash
# Run 1: Ollama
cp config/config_ollama.yaml config/config.yaml
./venv/bin/python -m src.cli project create "Tetris Test - Ollama"
# Execute all 7 milestones...

# Run 2: Codex
cp config/config_codex.yaml config/config.yaml
./venv/bin/python -m src.cli project create "Tetris Test - Codex"
# Execute all 7 milestones...

# Compare results
python scripts/compare_tetris_runs.py --run1 <project_id_ollama> --run2 <project_id_codex>
```

**Expected Time**: 25-35 hours total
**Best For**: Comprehensive flexible LLM validation
```

---

### 5. Success Criteria Updates (HIGH PRIORITY)

**Current State**: Success criteria don't mention LLM flexibility
**Required Update**: Add flexible LLM validation criteria

**Location**: `TETRIS_GAME_TEST_PLAN.md` - Section 6 (Success Criteria)

**Add to "Full Success" section**:

```markdown
✅ **Flexible LLM Validated**:
- Test completes successfully with Ollama (Qwen)
- Test completes successfully with OpenAI Codex
- Both LLM types produce functional game
- Quality scores differ by <20% between LLMs
- Decision patterns are similar (within 10% distribution)
- No LLM-specific bugs or failures
```

**Add New Failure Condition**:

```markdown
❌ **LLM-Specific Failures**:
- One LLM completes but the other fails critically
- Quality scores differ by >50% between LLMs
- Different final outcomes (one succeeds, one fails)
- LLM interface crashes or hangs consistently
```

---

### 6. Monitoring & Logging (LOW PRIORITY)

**Current State**: Logs don't distinguish LLM type
**Required Update**: Log which LLM is being used

**Location**: Throughout orchestration logs

**Log Format Update**:

**Before**:
```
[QWEN] Validating response...
[QWEN]   Quality: 0.81 (PASS)
```

**After** (more generic):
```
[LLM:ollama] Validating response...
[LLM:ollama]   Quality: 0.81 (PASS)
```

Or for Codex:
```
[LLM:openai-codex] Validating response...
[LLM:openai-codex]   Quality: 0.78 (PASS)
```

**Implementation**: Update `src/llm/local_interface.py` and `src/llm/openai_codex_interface.py` to include LLM type in log prefix.

---

### 7. Troubleshooting Section (MEDIUM PRIORITY)

**Current State**: Troubleshooting only covers Ollama issues
**Required Update**: Add Codex-specific troubleshooting

**Location**: `TETRIS_TEST_QUICK_START.md` - Troubleshooting section

**New Subsections**:

```markdown
### Codex-Specific Issues

#### Codex CLI Not Found
**Problem**: `PluginNotFoundError: LLM type 'openai-codex' not found`

**Solution**:
1. Verify Codex installed: `which codex`
2. If not found, install: `npm install -g @openai/codex-cli`
3. Configure path in config: `codex_command: /path/to/codex`

#### Rate Limiting (Codex)
**Problem**: `Rate limit exceeded` errors

**Solution**:
1. Check Codex subscription status
2. Add delay between prompts (already handled by orchestrator)
3. Consider upgrading Codex plan or switching to Ollama

#### Network Errors (Codex)
**Problem**: `Connection timeout` or `Network unreachable`

**Solution**:
1. Check internet connectivity
2. Increase timeout: `timeout: 120` in config
3. Switch to Ollama for offline development

#### Different Results Between LLMs
**Problem**: Ollama completes successfully, Codex fails (or vice versa)

**Solution**:
1. Compare quality scores - may indicate prompt sensitivity
2. Review decision patterns - check for CLARIFY loops
3. Check logs for LLM-specific errors
4. Report as flexible LLM bug (not expected behavior)
```

---

## Implementation Priority

### Phase 1: Critical Updates (1-2 hours)
1. ✅ Update configuration section in Quick Start
2. ✅ Add CLI command examples with LLM selection
3. ✅ Update success criteria in Test Plan
4. ✅ Add Codex troubleshooting section

### Phase 2: Validation Testing (20-40 hours)
1. ⏳ Run Tetris test with Ollama (baseline)
2. ⏳ Run Tetris test with Codex (comparative)
3. ⏳ Document results and differences
4. ⏳ Create comparison report

### Phase 3: Documentation Finalization (2-3 hours)
1. ⏳ Add comparison testing section
2. ⏳ Update monitoring/logging examples
3. ⏳ Create example configuration profiles
4. ⏳ Add lessons learned

---

## Risk Assessment

### Low Risk Updates
✅ Configuration documentation (no code changes)
✅ CLI command examples (already supported)
✅ Troubleshooting additions (informational)

### Medium Risk Updates
⚠️ Comparison testing framework (new scripts needed)
⚠️ Log format changes (may break existing log parsers)

### High Risk Updates
❌ None identified

---

## Expected Outcomes

### Minimum Success
✅ Tetris test runs successfully with **either** Ollama or Codex
✅ Documentation updated to reflect both options
✅ Users can choose LLM type via configuration

### Full Success
✅ Tetris test runs successfully with **both** Ollama and Codex
✅ Comparative analysis shows acceptable differences (<20% quality scores)
✅ Both LLM types produce functional game
✅ Comprehensive documentation with examples for both

### Stretch Goals
✅ Automated comparison testing script
✅ LLM selection via CLI flags (`--llm-type`)
✅ Configuration profiles for quick switching
✅ Side-by-side result dashboard

---

## Files to Update

### Documentation Files (High Priority)
1. **`docs/archive/development/tetris-test/TETRIS_TEST_QUICK_START.md`**
   - Add LLM configuration section
   - Update CLI commands with LLM selection
   - Add Codex troubleshooting

2. **`docs/archive/development/tetris-test/TETRIS_GAME_TEST_PLAN.md`**
   - Add flexible LLM comparison section
   - Update success criteria
   - Add monitoring metrics for LLM comparison

3. **`docs/archive/development/tetris-test/TETRIS_MILESTONE_SUMMARY.md`**
   - Add note about LLM flexibility at top
   - Reference configuration options

### Configuration Files (Medium Priority)
4. **`config/profiles/tetris_ollama.yaml`** (NEW)
   - Tetris test with Ollama configuration

5. **`config/profiles/tetris_codex.yaml`** (NEW)
   - Tetris test with Codex configuration

### Scripts (Low Priority)
6. **`scripts/compare_tetris_runs.py`** (NEW)
   - Compare two Tetris test runs (Ollama vs Codex)
   - Generate comparison report

---

## Validation Plan

### Step 1: Documentation Review
- [ ] Read updated docs for clarity
- [ ] Verify all links work
- [ ] Check for consistency

### Step 2: Configuration Testing
- [ ] Create `tetris_ollama.yaml` profile
- [ ] Create `tetris_codex.yaml` profile
- [ ] Test profile switching

### Step 3: Single-LLM Validation
- [ ] Run Milestone 1 with Ollama
- [ ] Run Milestone 1 with Codex
- [ ] Compare results

### Step 4: Full Test Execution (Optional)
- [ ] Run all 7 milestones with Ollama
- [ ] Run all 7 milestones with Codex
- [ ] Generate comparison report
- [ ] Document lessons learned

---

## Next Steps

### Immediate (Today)
1. Review this analysis document
2. Decide on implementation priority (Phase 1 only vs full implementation)
3. Create todo list for documentation updates

### Short-Term (This Week)
1. Update Quick Start guide with LLM configuration section
2. Update Test Plan with flexible LLM criteria
3. Add Codex troubleshooting section

### Long-Term (Optional)
1. Run comparative Tetris test with both LLMs
2. Create comparison testing framework
3. Add automated LLM selection to CLI

---

## Conclusion

The Tetris game development test is an **excellent validation target** for the flexible LLM orchestrator feature. The test's long-running, multi-session nature (7 milestones, 10-14 hours) will thoroughly stress the LLM interface and reveal any subtle differences between Ollama and OpenAI Codex orchestration.

**Key Benefits of Updating Tetris Test**:
1. ✅ Real-world validation of flexible LLM across complex, multi-session orchestration
2. ✅ Demonstrates subscription deployment model (Codex) for potential customers
3. ✅ Provides A/B testing data on LLM performance differences
4. ✅ Validates plugin architecture works correctly with both LLM types

**Recommended Approach**:
- **Phase 1 (Critical)**: Update documentation NOW (1-2 hours)
- **Phase 2 (Validation)**: Run comparison test when ready (20-40 hours)
- **Phase 3 (Polish)**: Finalize docs after validation (2-3 hours)

**Status**: ✅ Analysis complete - Ready for implementation

---

**Last Updated**: November 5, 2025
**Next Action**: Review analysis and approve Phase 1 documentation updates
