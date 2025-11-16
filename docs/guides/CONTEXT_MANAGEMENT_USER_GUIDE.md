# Context Management System - User Guide

**Document Type**: User Documentation
**Audience**: Obra Users & Operators
**Status**: Production Ready
**Version**: 1.0.0
**Date**: 2025-01-15

---

## Quick Start

The context management system automatically manages the Orchestrator LLM's context window, preventing overflow and maintaining session continuity.

### Basic Usage

```python
from src.orchestration.memory.memory_manager import MemoryManager

# Initialize (auto-detects context window)
manager = MemoryManager(
    model_config={
        'provider': 'ollama',
        'model': 'qwen2.5-coder:32b'
    }
)

# Add operations
manager.add_operation({
    'type': 'task',
    'operation': 'create_task',
    'data': {'title': 'Implement feature'},
    'tokens': 500  # Optional - auto-estimated if missing
})

# Build optimized context for LLM
context = manager.build_context(optimize=True)

# Check status
status = manager.get_status()
print(f"Zone: {status['window_manager']['zone']}")

# Checkpoint when needed
if manager.should_checkpoint():
    checkpoint_path = manager.checkpoint()
```

---

## Configuration

### Optimization Profiles

The system auto-selects an optimization profile based on your context window size:

| Context Size | Profile | Description |
|--------------|---------|-------------|
| 4K-8K | Ultra-Aggressive | Maximum compression for tiny contexts |
| 8K-32K | Aggressive | Balanced compression for small contexts |
| 32K-100K | Balanced-Aggressive | Light compression for medium contexts |
| 100K-250K | Balanced | Minimal compression for large contexts |
| 250K+ | Minimal | Almost no compression for huge contexts |

### Manual Override

Override the auto-selected profile when needed:

```python
manager = MemoryManager(
    model_config={'context_window': 128000},
    config={'profile_override': 'aggressive'}  # Force more aggressive
)
```

**When to override**:
- **Testing**: Use aggressive profile to stress-test
- **Production**: Use conservative profile for safety
- **Batch jobs**: Use minimal profile for throughput
- **Interactive**: Use balanced for responsiveness

### Custom Configuration

```python
config = {
    'artifact_storage_path': '.obra/memory/artifacts',
    'checkpoint_dir': '.obra/memory/checkpoints',
    'utilization_limit': 0.85,  # Use 85% of context
    'summarization_threshold': 500,
    'externalization_threshold': 2000,
}

manager = MemoryManager(
    model_config={'context_window': 128000},
    config=config
)
```

---

## Usage Patterns

### Pattern 1: Simple Workflow

```python
# Initialize
manager = MemoryManager(model_config={'context_window': 128000})

# Track work
for task in tasks:
    manager.add_operation({
        'type': 'task',
        'operation': 'execute',
        'data': task,
        'tokens': estimate_tokens(task)
    })

# Build context before LLM call
context = manager.build_context()
llm_response = llm.generate(context)
```

### Pattern 2: Long Session with Checkpoints

```python
manager = MemoryManager(model_config={'context_window': 128000})

for iteration in range(100):
    # Do work
    manager.add_operation(...)

    # Periodic checkpoint
    if manager.should_checkpoint():
        checkpoint_path = manager.checkpoint()
        logger.info(f"Checkpoint created: {checkpoint_path}")
```

### Pattern 3: Session Resume

```python
# Save session
checkpoint_path = manager.checkpoint()

# Later... resume session
manager = MemoryManager(model_config={'context_window': 128000})
manager.restore(checkpoint_path)

# Continue work
manager.add_operation(...)
```

---

## Context Zones

The system tracks context usage across 4 zones:

| Zone | Usage | Action | Description |
|------|-------|--------|-------------|
| 🟢 **Green** | <50% | Proceed normally | Safe operation zone |
| 🟡 **Yellow** | 50-70% | Monitor, plan checkpoint | Approaching limits |
| 🟠 **Orange** | 70-85% | Optimize then checkpoint | Near capacity |
| 🔴 **Red** | >85% | Emergency checkpoint | Critical |

```python
status = manager.get_status()
zone = status['window_manager']['zone']

if zone == 'orange':
    # Optimize and checkpoint
    context = manager.build_context(optimize=True)
    manager.checkpoint()
elif zone == 'red':
    # Emergency actions
    manager.checkpoint()
    manager.clear()  # Reset if needed
```

---

## Optimization Techniques

The system applies 5 optimization techniques automatically:

1. **Pruning**: Remove old debug traces and temporary data
2. **Artifact Registry**: Replace file contents with metadata references
3. **External Storage**: Move large items (>2000 tokens) to disk
4. **Differential State**: Store only state changes, not full snapshots
5. **Summarization**: Compress completed phases (requires LLM interface)

### Controlling Optimization

```python
# Full optimization (recommended)
context = manager.build_context(optimize=True)

# No optimization (for debugging or high-throughput)
context = manager.build_context(optimize=False)
```

---

## Monitoring & Debugging

### Get Detailed Status

```python
status = manager.get_status()

print(f"Profile: {status['optimization_profile']['name']}")
print(f"Operations: {status['working_memory']['operation_count']}")
print(f"Tokens used: {status['window_manager']['used_tokens']:,}")
print(f"Zone: {status['window_manager']['zone']}")
print(f"Checkpoint needed: {status['checkpoint_needed']}")
```

### Query Recent Operations

```python
# Get last 10 operations
recent = manager.get_recent_operations(limit=10)

# Get operations by type
tasks = manager.get_recent_operations(operation_type='task')
validations = manager.get_recent_operations(operation_type='validation')
```

### Working Memory Status

```python
wm_status = manager.working_memory.get_status()

print(f"Operations: {wm_status['operation_count']}/{wm_status['max_operations']}")
print(f"Tokens: {wm_status['current_tokens']:,}/{wm_status['max_tokens']:,}")
print(f"Evictions: {wm_status['eviction_count']}")
```

---

## Troubleshooting

### Issue: Frequent Evictions

**Symptom**: `eviction_count` increasing rapidly

**Causes**:
- Operations too large for working memory
- Profile too aggressive for use case

**Solutions**:
```python
# 1. Use less aggressive profile
config = {'profile_override': 'balanced'}

# 2. Increase working memory (if context allows)
# Edit config/optimization_profiles.yaml
# Increase max_operations or max_tokens_pct

# 3. Reduce operation token counts
manager.add_operation({
    'type': 'task',
    'tokens': 300  # Smaller tokens
})
```

### Issue: Red Zone Warnings

**Symptom**: `zone == 'red'` frequently

**Causes**:
- Too many large operations
- Checkpoint interval too long
- Insufficient optimization

**Solutions**:
```python
# 1. Enable optimization
context = manager.build_context(optimize=True)

# 2. More frequent checkpoints
if manager.should_checkpoint():
    manager.checkpoint()
    # Optional: clear after checkpoint
    manager.clear()

# 3. Use more aggressive profile
config = {'profile_override': 'aggressive'}
```

### Issue: Slow Context Building

**Symptom**: `build_context()` takes >1 second

**Causes**:
- Too many operations
- Optimization overhead
- Large operation payloads

**Solutions**:
```python
# 1. Disable optimization for speed
context = manager.build_context(optimize=False)

# 2. Checkpoint and clear more often
if len(manager.get_recent_operations()) > 100:
    manager.checkpoint()
    manager.clear()

# 3. Reduce operation payload sizes
# Keep 'data' fields small, move large data to external storage
```

### Issue: Large Checkpoint Files

**Symptom**: Checkpoint files >1MB

**Causes**:
- Too many operations in memory
- Large operation payloads

**Solutions**:
```python
# 1. Checkpoint more frequently (fewer ops per checkpoint)
if manager._operation_count >= 100:
    manager.checkpoint()
    manager.clear()

# 2. Enable external storage in profile
# Large items will be moved to disk instead of checkpoint

# 3. Reduce operation data
# Keep only essential data in operations
```

---

## Best Practices

### 1. Let Auto-Selection Work

✅ **DO**: Trust the automatic profile selection
```python
# Good - auto-selects based on context
manager = MemoryManager(model_config={'context_window': 128000})
```

❌ **DON'T**: Override unless you have specific needs
```python
# Avoid - only override with good reason
manager = MemoryManager(
    model_config={'context_window': 128000},
    config={'profile_override': 'ultra_aggressive'}  # Probably too aggressive
)
```

### 2. Use Checkpoints Regularly

✅ **DO**: Checkpoint based on recommendations
```python
if manager.should_checkpoint():
    manager.checkpoint()
```

❌ **DON'T**: Ignore checkpoint recommendations
```python
# Risky - may lose context
# (no checkpointing code)
```

### 3. Monitor Zone Transitions

✅ **DO**: Log zone changes
```python
status = manager.get_status()
if status['window_manager']['zone'] != last_zone:
    logger.info(f"Zone transition: {last_zone} → {status['window_manager']['zone']}")
```

### 4. Token Estimation

✅ **DO**: Provide accurate token counts
```python
manager.add_operation({
    'type': 'task',
    'data': task_data,
    'tokens': calculate_tokens(task_data)  # Accurate
})
```

⚠️ **ACCEPTABLE**: Let system estimate
```python
manager.add_operation({
    'type': 'task',
    'data': task_data
    # 'tokens' omitted - system estimates
})
```

### 5. Clear After Major Operations

✅ **DO**: Clear when starting new phase
```python
# After completing a major phase
manager.checkpoint()  # Save state
manager.clear()       # Start fresh
```

---

## Performance Tips

### High Throughput

```python
# Disable optimization for maximum speed
context = manager.build_context(optimize=False)

# Use minimal profile
config = {'profile_override': 'minimal'}

# Larger working memory
# (Edit config/optimization_profiles.yaml)
```

### Low Memory

```python
# Use aggressive profile
config = {'profile_override': 'aggressive'}

# Enable all optimizations
context = manager.build_context(optimize=True)

# Frequent checkpoints and clears
if manager.should_checkpoint():
    manager.checkpoint()
    manager.clear()
```

### Interactive Sessions

```python
# Use balanced profile (default for 100K-250K)
# Moderate optimization
context = manager.build_context(optimize=True)

# Checkpoint periodically (not every operation)
if manager._operation_count % 50 == 0:
    manager.checkpoint()
```

---

## Advanced Topics

### Custom Thresholds

```python
custom_thresholds = {
    'green_upper': 0.40,    # More conservative green zone
    'yellow_upper': 0.60,   # Earlier yellow zone
    'orange_upper': 0.80,   # Earlier orange zone
}

manager = MemoryManager(
    model_config={'context_window': 128000},
    config={'custom_thresholds': custom_thresholds}
)
```

### LLM Interface for Summarization

```python
# Provide LLM interface for advanced summarization
llm_interface = MyLLMInterface()

manager = MemoryManager(
    model_config={'context_window': 128000},
    llm_interface=llm_interface
)

# Now summarization technique is available
context = manager.build_context(optimize=True)
```

---

## See Also

- **Architecture**: `docs/design/ORCHESTRATOR_CONTEXT_MANAGEMENT_DESIGN_V2.md`
- **Performance**: `docs/performance/CONTEXT_MANAGEMENT_BENCHMARKS.md`
- **API Reference**: Public class methods and configuration options
- **Profiles**: `config/optimization_profiles.yaml`

---

## Support

For issues or questions:
1. Check logs for zone transitions and warnings
2. Review `manager.get_status()` output
3. Consult troubleshooting section above
4. Check GitHub issues for similar problems

**Document Version**: 1.0.0
**Last Updated**: 2025-01-15
