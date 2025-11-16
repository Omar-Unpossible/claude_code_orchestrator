# Small Context Window Deployment Guide

**Document Type**: User Guide
**Date**: 2025-01-15
**Target Audience**: Users deploying Obra with local LLMs (4K-32K context windows)
**Related**: ADR-018 (Orchestrator Context Management)

---

## Overview

This guide helps you deploy and configure Obra with **small context window LLMs** (4K-32K tokens), common for local models running on consumer hardware. Small contexts require special configuration to prevent overflow while maintaining functionality.

**Common Small Context Models**:
- **Phi-3 Mini** (4K context) - Microsoft's efficient small model
- **Qwen 2.5 Coder 3B** (8K context) - Alibaba's coding model
- **Qwen 2.5 Coder 7B** (16K context) - Balanced performance/size
- **LLaMA 3.1 8B** (8K-32K context) - Meta's open model
- **Mistral 7B** (8K-32K context) - Mistral AI's efficient model

---

## Quick Start

### 1. Configure Your Model

Edit `config/models.yaml`:

```yaml
llm_models:
  # Example: Phi-3 Mini (4K context)
  phi_3_mini:
    provider: ollama
    model: phi3:mini
    context_window: 4096
    optimization_profile: ultra-aggressive

  # Example: Qwen 2.5 Coder 7B (16K context)
  qwen_2.5_7b:
    provider: ollama
    model: qwen2.5-coder:7b
    context_window: 16384
    optimization_profile: aggressive

# Set as active model
active_orchestrator_model: qwen_2.5_7b  # Change to your model
```

### 2. Verify Auto-Detection

Run Obra and check context detection:

```bash
$ python -m src.cli interactive

[INFO] ContextWindowManager initialized: qwen2.5-coder:7b, 16,384 tokens, optimization_profile=aggressive
```

### 3. Adjust Utilization Limit (Optional)

If you want to use only 75% of available context for safety:

Edit `config/default_config.yaml`:

```yaml
orchestrator:
  context_window:
    utilization_limit: 0.75  # Use 75% of 16K = 12K effective max
```

---

## Context Size Recommendations

### Ultra-Small: 4K-8K (Phi-3 Mini, Qwen 3B)

**Configuration**:
```yaml
orchestrator:
  context_window:
    max_tokens: 4096  # or 8192
    utilization_limit: 0.8  # Use 80% for safety (3.2K or 6.5K)

  working_memory:
    max_operations: 10  # Keep only last 10 operations

  checkpoint:
    time_interval_hours: 0.5  # Checkpoint every 30 minutes
    operation_interval: 20  # Checkpoint every 20 operations
```

**Usage Tips**:
- **Work in small batches**: Create 1-3 tasks at a time, complete before adding more
- **Frequent checkpoints**: Context fills quickly, checkpoint every 30 min recommended
- **Minimal history**: System keeps only last 10 operations in memory
- **Short sessions**: Plan for 30-60 min sessions, longer sessions will checkpoint often

**What to Expect**:
- ✅ Basic NL commands work ("create task", "list tasks")
- ✅ Short reference resolution ("create epic X", "add story to it")
- ⚠️ Limited operation history (last 10 commands only)
- ⚠️ Frequent checkpoint notifications (every 20-30 operations)
- ❌ Complex multi-step workflows may require multiple sessions

### Small: 8K-32K (Qwen 7B, Mistral 7B, LLaMA 8B)

**Configuration**:
```yaml
orchestrator:
  context_window:
    max_tokens: 16384  # or 32768
    utilization_limit: 0.85  # Use 85% (13.9K or 27.8K)

  working_memory:
    max_operations: 30  # Last 30 operations

  checkpoint:
    time_interval_hours: 1.0  # Checkpoint every hour
    operation_interval: 50  # Checkpoint every 50 operations
```

**Usage Tips**:
- **Moderate batches**: Create 5-10 tasks at a time
- **Hourly checkpoints**: Context fills moderately, checkpoint every hour
- **Decent history**: Last 30 operations tracked
- **1-2 hour sessions**: Comfortable session length

**What to Expect**:
- ✅ Full NL command support
- ✅ Reference resolution works well
- ✅ Moderate operation history (last 30 commands)
- ✅ Checkpoint every hour (less disruptive)
- ⚠️ Large epics (10+ stories) may need multiple sessions

### Medium-Small: 32K-100K (Qwen 14B, larger models)

**Configuration**:
```yaml
orchestrator:
  context_window:
    max_tokens: 65536  # or up to 100000
    utilization_limit: 0.9  # Use 90%

  working_memory:
    max_operations: 50

  checkpoint:
    time_interval_hours: 2.0
    operation_interval: 100
```

**Usage Tips**:
- **Large batches**: Create 10-20 tasks at a time
- **2-hour checkpoints**: Comfortable checkpoint frequency
- **Good history**: Last 50 operations tracked
- **2-4 hour sessions**: Extended work sessions

**What to Expect**:
- ✅ All features work smoothly
- ✅ Complex workflows supported
- ✅ Large operation history
- ✅ Infrequent checkpoints (every 2 hours)

---

## Optimization Strategies by Context Size

### Ultra-Aggressive (4K-8K)

**Automatic Optimizations**:
- Summarize anything >100 tokens
- Keep only last 10 operations in working memory
- Session memory: Single paragraph (≤200 tokens)
- Project state: ≤300 tokens
- Work plan: ≤200 tokens
- Decision log: Last 3 decisions only
- Checkpoint every 30 minutes

**Manual Optimizations**:
- Use short, direct NL commands ("create task X" not "I would like to create a task called X...")
- Avoid verbose descriptions (keep task descriptions <100 chars)
- Work on 1 epic at a time
- Complete and archive old epics regularly

### Aggressive (8K-32K)

**Automatic Optimizations**:
- Summarize anything >300 tokens
- Keep last 30 operations
- Session memory: Compressed narrative (≤500 tokens)
- Project state: ≤800 tokens
- Work plan: ≤500 tokens
- Decision log: Last 5 decisions
- Checkpoint every 1 hour

**Manual Optimizations**:
- Keep task descriptions concise (<200 chars)
- Archive completed epics
- Use `/checkpoint` command before starting large operations

---

## Troubleshooting

### Issue: "Context overflow detected" errors

**Cause**: Context exceeded 95% threshold without checkpoint

**Solution**:
1. Reduce `utilization_limit` to 0.75 or 0.80
2. Decrease `checkpoint.time_interval_hours` (e.g., 0.5 for 4K, 1.0 for 16K)
3. Decrease `checkpoint.operation_interval` (e.g., 20 for 4K, 50 for 16K)
4. Manually trigger checkpoints: `/checkpoint`

### Issue: Checkpoints too frequent (disruptive)

**Cause**: Aggressive optimization profile for small context

**Solution**:
1. Increase context window if possible (upgrade to larger model)
2. Accept frequent checkpoints as necessary for small contexts
3. Use utilization_limit=1.0 to maximize available space (less safe)
4. Work in shorter sessions (30-60 min for 4K, 1-2 hours for 16K)

### Issue: Reference resolution doesn't work ("it", "that")

**Cause**: Working memory too small, previous operation evicted

**Solution**:
1. Use references immediately after creating entities
   - ✅ Good: "Create epic X. Add story Y to it."
   - ❌ Bad: "Create epic X. [10 commands later] Add story Y to it."
2. Use explicit IDs instead of references
   - ✅ "Add story Y to epic 5"
   - Instead of: "Add story Y to it"
3. Increase `working_memory.max_operations` if context allows

### Issue: Auto-detection fails (uses 16K fallback)

**Cause**: Ollama API unavailable or model not found

**Solution**:
1. Verify Ollama is running: `ollama list`
2. Manually set context window in `config/models.yaml`:
   ```yaml
   my_model:
     context_window: 8192  # Set explicitly
   ```
3. Check Ollama API: `curl http://localhost:11434/api/show -d '{"name": "qwen2.5-coder:7b"}'`

### Issue: Performance slow after checkpoint

**Cause**: Checkpoint compression using LLM (2-5 seconds)

**Solution**:
- This is expected behavior (target <5s)
- If >5s, check LLM performance (may need faster model)
- Checkpoints run in background for most operations
- Critical checkpoints (85% threshold) may pause briefly

---

## Best Practices for Small Contexts

### 1. Plan Your Work

**Before starting**:
- Know what you want to accomplish
- Break large features into small epics (3-5 stories each)
- Plan for multiple sessions if needed

**During work**:
- Complete one epic before starting another
- Archive finished epics regularly
- Use `/status` to monitor context usage

### 2. Use Efficient Commands

**Efficient NL Commands**:
- ✅ "Create epic user auth"
- ✅ "Add story login to epic 5"
- ✅ "List open tasks"

**Inefficient NL Commands**:
- ❌ "I would like to create an epic called user authentication system with OAuth and MFA support"
- ❌ "Can you please add a story for implementing the login functionality to the epic we just created?"

### 3. Monitor Context Usage

**Check current usage**:
```bash
# In interactive mode
/status

# Output shows:
Context: 8,234 / 16,384 tokens (50.3%) - Green Zone
```

**Zones**:
- 🟢 Green (<50%): Normal operation
- 🟡 Yellow (50-70%): Plan checkpoint soon
- 🟠 Orange (70-85%): Checkpoint recommended
- 🔴 Red (>85%): Checkpoint mandatory

### 4. Leverage Checkpoints

**Manual checkpoint before large operations**:
```bash
# Before creating big epic with many stories
/checkpoint
create epic user authentication with 10 stories...
```

**Resume from checkpoint after crash**:
```bash
# Obra auto-resumes from last checkpoint
# Check .obra/checkpoints/ for checkpoint files
```

### 5. Archive Regularly

**Archive completed epics**:
- Removes from active context
- Preserves in database (can still query)
- Frees context for new work

```python
# (Future feature - manual archive command)
/archive epic 5
```

---

## Configuration Examples

### Example 1: Phi-3 Mini (4K) - Minimal Setup

```yaml
# config/models.yaml
llm_models:
  phi_3_mini_4k:
    provider: ollama
    model: phi3:mini
    context_window: 4096
    optimization_profile: ultra-aggressive

active_orchestrator_model: phi_3_mini_4k

# config/default_config.yaml
orchestrator:
  context_window:
    auto_detect: true
    utilization_limit: 0.75  # 3K effective

  working_memory:
    max_operations: 10

  checkpoint:
    time_interval_hours: 0.5
    operation_interval: 20

  optimization:
    phase_summary_max_tokens: 100  # Very aggressive
```

### Example 2: Qwen 2.5 Coder 7B (16K) - Balanced

```yaml
# config/models.yaml
llm_models:
  qwen_7b_16k:
    provider: ollama
    model: qwen2.5-coder:7b
    context_window: 16384
    optimization_profile: aggressive

active_orchestrator_model: qwen_7b_16k

# config/default_config.yaml
orchestrator:
  context_window:
    auto_detect: true
    utilization_limit: 0.85  # 13.9K effective

  working_memory:
    max_operations: 30

  checkpoint:
    time_interval_hours: 1.0
    operation_interval: 50

  optimization:
    phase_summary_max_tokens: 300
```

### Example 3: Conservative (Maximize Safety)

```yaml
# config/default_config.yaml
orchestrator:
  context_window:
    auto_detect: true
    utilization_limit: 0.65  # Very conservative - 65% of available

  checkpoint:
    time_interval_hours: 0.25  # Checkpoint every 15 minutes
    operation_interval: 15  # Checkpoint every 15 operations

  # Manual profile override (more aggressive than auto-select)
  optimization_profile: ultra-aggressive
```

---

## Performance Expectations

### 4K Context (Phi-3 Mini)

| Metric | Expected Value |
|--------|----------------|
| Max operations in memory | 10 |
| Checkpoint frequency | Every 20-30 operations or 30 min |
| Session duration | 30-60 minutes |
| Epics per session | 1-2 small epics (3-5 stories each) |
| Reference resolution window | Last 5-10 commands |

### 16K Context (Qwen 7B)

| Metric | Expected Value |
|--------|----------------|
| Max operations in memory | 30 |
| Checkpoint frequency | Every 50 operations or 1 hour |
| Session duration | 1-2 hours |
| Epics per session | 2-3 medium epics (5-10 stories each) |
| Reference resolution window | Last 20-30 commands |

### 32K Context (Larger models)

| Metric | Expected Value |
|--------|----------------|
| Max operations in memory | 50 |
| Checkpoint frequency | Every 100 operations or 2 hours |
| Session duration | 2-4 hours |
| Epics per session | 3-5 epics |
| Reference resolution window | Last 40-50 commands |

---

## FAQ

**Q: Can I use Obra with a 4K context model?**
A: Yes, but with limitations. You'll have frequent checkpoints, minimal operation history, and should work in short sessions (30-60 min). Recommended for simple projects only.

**Q: How do I know if my context is too small?**
A: Signs: Checkpoints every 10-15 minutes, reference resolution fails frequently, "context overflow" warnings, sessions <30 minutes.

**Q: Should I increase `utilization_limit` to 1.0?**
A: Only if you're comfortable with risk. Higher limits = less safety margin. Recommended: 0.75-0.85 for small contexts.

**Q: What's the minimum viable context window?**
A: 4K works but is very constrained. 8K is minimal for comfortable use. 16K is recommended for most workflows.

**Q: Can I upgrade to a larger model later?**
A: Yes! Just change `active_orchestrator_model` in `config/models.yaml`. Existing checkpoints and data will work fine.

**Q: Do checkpoints slow down my work?**
A: Checkpoints take 2-5 seconds (LLM summarization). Time-based checkpoints run in background. Threshold-based (70%, 85%) may pause briefly.

---

## Related Documentation

- **ADR-018**: Orchestrator Context Management (architecture decision)
- **ORCHESTRATOR_CONTEXT_MANAGEMENT_DESIGN_V2.md**: Detailed design specification
- **Configuration Reference**: `config/default_config.yaml` (all options)
- **Model Configuration**: `config/models.yaml` (model definitions)

---

**Last Updated**: 2025-01-15
**Version**: 1.0
**Applies to**: Obra v1.8.0+ (with ADR-018 implementation)
