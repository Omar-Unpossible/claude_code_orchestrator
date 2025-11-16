# ADR-018: Orchestrator Context Management System

**Status**: Accepted
**Date**: 2025-01-15
**Decision Makers**: System Architecture Team
**Related**: ADR-011 (Session Management), ADR-017 (Unified Execution)

---

## Context

The Orchestrator (local Qwen LLM) currently operates statelessly, rebuilding context from StateManager for each operation. This approach has significant limitations:

**Problem Statement**:
1. **No memory continuity**: Cannot answer "what did we just do?" or resolve references like "add 3 stories to it"
2. **No context window tracking**: Orchestrator doesn't monitor its own token usage, risking overflow
3. **Inefficient rebuilds**: Queries StateManager repeatedly for same data
4. **No big-picture awareness**: Cannot maintain project state understanding over long sessions
5. **Variable context windows**: Local LLMs range from 4K (minimal) to 1M+ (future), requiring adaptive strategies
6. **User preferences**: Some users may want to limit context usage to 75% of capacity for quality/safety

**Why This Matters**:
- Long interactive sessions (50+ NL commands) can exceed context limits without warning
- Complex projects (1000+ tasks) cannot fit in context without intelligent management
- Local LLMs often have much smaller contexts (4K-32K) than cloud models (200K-1M)
- Reference resolution ("it", "that") requires recent operation memory
- Cross-session continuity needs persistent state beyond database queries

**Current State**:
- Implementer (Claude Code) has session management (ADR-011)
- Orchestrator has NO context management
- StateManager provides durable storage but not working memory
- ContextManager builds prompts but doesn't track Orchestrator's own usage

---

## Decision

We will implement a **multi-tier memory architecture** for the Orchestrator with **full configurability** for context windows ranging from 4K to 1M+ tokens.

### Architecture Overview

**Four Memory Tiers**:

```
Tier 1: Working Memory (In-Process)
  - Last 10-100 operations (adaptive based on context size)
  - FIFO eviction, fast access
  - 5-10% of context window

Tier 2: Session Memory (Documents)
  - Current session narrative
  - Compressed when threshold reached
  - 15-30% of context window

Tier 3: Episodic Memory (Long-term Docs)
  - Project state, work plan, decision log
  - Persistent across sessions
  - 25-40% of context window

Tier 4: Semantic Memory (Database)
  - StateManager (existing)
  - Query on-demand, not loaded by default
  - Reference only (not part of context)
```

### Context Window Management Strategy

**Industry-Standard Thresholds** (percentages of configured context window):
- **<50%**: 🟢 Green zone - normal operation
- **50-70%**: 🟡 Yellow zone - monitor, plan checkpoint
- **70-85%**: 🟠 Orange zone - optimize, then checkpoint
- **>85%**: 🔴 Red zone - mandatory checkpoint

**Adaptive Optimization Profiles**:

| Context Window Size | Profile | Optimization Strategy |
|---------------------|---------|----------------------|
| 4K-8K (Ultra-small) | Ultra-aggressive | Summarize >100 tokens, checkpoint every 30 min, keep last 10 ops |
| 8K-32K (Small) | Aggressive | Summarize >300 tokens, checkpoint every 1 hour, keep last 30 ops |
| 32K-100K (Medium-small) | Balanced-aggressive | Summarize >500 tokens, checkpoint every 2 hours, keep last 50 ops |
| 100K-250K (Medium) | Balanced | Summarize >500 tokens, checkpoint every 4 hours, keep last 50 ops |
| 250K+ (Large) | Minimal | Summarize >1000 tokens, checkpoint every 8 hours, keep last 100 ops |

**Configuration Options**:

```yaml
orchestrator:
  context_window:
    # Auto-detection
    auto_detect: true  # Query LLM for max context (recommended)

    # Manual override (if auto-detect fails or user preference)
    max_tokens: null  # null = auto-detect, or specify: 4096, 8192, 16384, 32768, 128000, 200000, etc.

    # User preference limit (use less than available)
    utilization_limit: 1.0  # 1.0 = 100%, 0.75 = 75%, 0.5 = 50%
    # Example: 128K context with 0.75 limit = effective 96K max usage

    # Thresholds (percentages of effective max)
    green_threshold: 0.50
    yellow_threshold: 0.70
    orange_threshold: 0.85
    red_threshold: 0.95

    # Fallback if detection fails
    fallback_size: 16384  # Conservative 16K fallback
```

### Context Optimization Techniques

**Five Industry-Standard Techniques**:

1. **Summarization**: Collapse completed phases to ≤500 tokens (or ≤100 for ultra-small contexts)
2. **Artifact Registry**: File → summary mappings instead of full contents
3. **Differential State**: Store only changes since checkpoint, not full snapshots
4. **External Storage**: Move large data (>2000 tokens) to files, reference by path
5. **Explicit Pruning**: Remove debug traces >1hr, keep only last 5 validations, etc.

### Small Context Window Strategies

For deployments with 4K-32K contexts (common for local LLMs):

**Ultra-Small (4K-8K)**:
- **Working Memory**: Last 10 operations only
- **Session Memory**: Single paragraph summary (≤200 tokens)
- **Episodic Memory**:
  - Project state: ≤300 tokens
  - Work plan: ≤200 tokens
  - Decision log: Last 3 decisions only (≤100 tokens each)
- **Checkpoint Frequency**: Every 30 minutes or 20 operations
- **Optimization**: Aggressive - summarize everything >100 tokens

**Small (8K-32K)**:
- **Working Memory**: Last 30 operations
- **Session Memory**: Compressed narrative (≤500 tokens)
- **Episodic Memory**:
  - Project state: ≤800 tokens
  - Work plan: ≤500 tokens
  - Decision log: Last 5 decisions (≤200 tokens each)
- **Checkpoint Frequency**: Every 1 hour or 50 operations
- **Optimization**: Aggressive - summarize everything >300 tokens

**Medium-Small (32K-100K)**:
- **Working Memory**: Last 50 operations
- **Session Memory**: Detailed narrative (≤3000 tokens)
- **Episodic Memory**:
  - Project state: ≤5000 tokens
  - Work plan: ≤3000 tokens
  - Decision log: Last 10 decisions (≤300 tokens each)
- **Checkpoint Frequency**: Every 2 hours or 100 operations
- **Optimization**: Balanced-aggressive - summarize >500 tokens

### Checkpoint System

**Triggers** (any of):
1. **Threshold-based**: 70% (yellow) or 85% (orange) usage
2. **Time-based**: Configurable interval (default 4 hours, adaptive for small contexts)
3. **Operation-count**: Configurable (default 100 ops, adaptive for small contexts)
4. **Manual**: User-triggered via `/checkpoint` command

**Checkpoint Format**:
```json
{
  "checkpoint": {
    "id": "CP-20250115-143000",
    "timestamp": "2025-01-15T14:30:00Z",
    "trigger": "threshold_70pct",
    "context_snapshot": {
      "tokens_used": 89600,
      "percentage": 0.70,
      "effective_max": 128000,
      "configured_max": 128000,
      "utilization_limit": 1.0,
      "plan_manifest_path": ".obra/sessions/plan_manifest_v3.json",
      "phase_summary_path": ".obra/sessions/phase_summary_p2.md",
      "artifacts_registry_path": ".obra/memory/artifacts_v3.json",
      "decision_records_path": ".obra/decisions/"
    },
    "resume_instructions": {
      "next_task": "T2.3.1",
      "phase": "execution",
      "blockers": [],
      "context_to_load": ["plan_manifest", "current_phase_summary", "last_3_decision_records"]
    },
    "metadata": {
      "model": "qwen2.5-coder:32b",
      "context_window": 128000,
      "optimization_profile": "balanced",
      "session_duration_seconds": 7234
    }
  }
}
```

### Decision Records (ADR Pattern)

**Privacy-Compliant Logging**:
- ✅ **Log**: Structured decision records (context, decision, consequences, alternatives, assumptions)
- ❌ **Never log**: Raw chain-of-thought, scratchpad reasoning, internal deliberation

**Format**: Architecture Decision Record (ADR)
```markdown
# Decision Record: [Title]

**Date**: 2025-01-15
**Status**: Accepted
**ID**: DR-a3f8b2c1

## Context
[Brief problem description]

## Decision
[What was decided]

## Consequences
**Positive**: [Benefits]
**Negative**: [Drawbacks]
**Mitigations**: [How negatives are addressed]

## Alternatives Considered
1. **Option A**: [Rejected because...]
2. **Option B**: [Rejected because...]

## Assumptions
- [Key assumption 1]
- [Key assumption 2]
```

### Configuration System

**Model Definitions** (`config/models.yaml`):
```yaml
llm_models:
  # Ultra-small local models
  phi_3_mini:
    provider: ollama
    model: phi3:mini
    context_window: 4096
    optimization_profile: ultra-aggressive

  # Small local models
  qwen_2.5_3b:
    provider: ollama
    model: qwen2.5-coder:3b
    context_window: 8192
    optimization_profile: aggressive

  qwen_2.5_7b:
    provider: ollama
    model: qwen2.5-coder:7b
    context_window: 16384
    optimization_profile: aggressive

  # Medium local models
  qwen_2.5_32b:
    provider: ollama
    model: qwen2.5-coder:32b
    context_window: 128000
    optimization_profile: balanced

  # Large cloud models
  claude_3.5_sonnet:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
    context_window: 200000
    optimization_profile: balanced

  # Future large models
  gpt5_turbo:
    provider: openai
    model: gpt-5-turbo
    context_window: 1000000
    optimization_profile: minimal

active_orchestrator_model: qwen_2.5_32b
```

**Runtime Configuration** (`config/default_config.yaml`):
```yaml
orchestrator:
  # Context window detection and limits
  context_window:
    auto_detect: true
    max_tokens: null  # Auto-detect from model config
    utilization_limit: 1.0  # Use 100% of available (can set to 0.75, 0.5, etc.)
    fallback_size: 16384  # If detection fails

  # Adaptive settings (override auto-selection if needed)
  optimization_profile: null  # null = auto-select from model config

  # Working memory (adaptive based on context size)
  working_memory:
    max_operations: null  # null = adaptive (10 for 4K, 30 for 16K, 50 for 128K, 100 for 1M)
    max_tokens: null  # null = adaptive (5-10% of context window)

  # Checkpoint configuration
  checkpoint:
    triggers:
      threshold_based: true
      time_based: true
      operation_count_based: true

    # Adaptive intervals (smaller contexts = more frequent checkpoints)
    time_interval_hours: null  # null = adaptive (0.5 for 4K, 1 for 16K, 4 for 128K, 8 for 1M)
    operation_interval: null  # null = adaptive (20 for 4K, 50 for 16K, 100 for 128K, 200 for 1M)
```

---

## Consequences

### Positive

1. **Continuity**: Orchestrator maintains awareness across operations and sessions
2. **Efficiency**: Reduces redundant StateManager queries
3. **Scalability**: Supports 4K to 1M+ context windows with adaptive strategies
4. **Safety**: Prevents context overflow with proactive checkpointing
5. **Flexibility**: Users can limit context usage based on preferences (e.g., 75% for quality)
6. **Intelligence**: Enables reference resolution, big-picture awareness
7. **Future-proof**: Works with any LLM via model configuration
8. **Privacy**: ADR decision records comply with best practices (no raw reasoning)
9. **Small context support**: Optimized strategies for 4K-32K deployments (common for local LLMs)
10. **Auto-detection**: Automatically discovers context limits, minimal manual configuration

### Negative

1. **Complexity**: Adds ~2,500 lines of code and 6 new components
2. **Memory overhead**: ~20-100MB in-memory depending on context size
3. **Performance impact**: ~50ms context building overhead, ~3s checkpoint latency
4. **Configuration burden**: Users with non-standard deployments may need manual tuning
5. **Testing complexity**: Must test across 4K-1M range of context sizes
6. **Migration effort**: Existing sessions need checkpoint migration

### Mitigations

1. **Complexity**: Comprehensive tests (≥90% coverage), clear documentation, phased rollout
2. **Memory overhead**: Acceptable for modern systems (<100MB), configurable limits
3. **Performance**: Acceptable for interactive use (<5s checkpoint), async operations where possible
4. **Configuration**: Intelligent defaults work for 95% of deployments, auto-detection reduces manual config
5. **Testing**: Automated tests with mock contexts (4K, 16K, 128K, 1M), real LLM integration tests
6. **Migration**: Automated migration script, backward compatibility mode

---

## Alternatives Considered

### Alternative 1: No Context Management (Status Quo)

**Pros**:
- No implementation cost
- No additional complexity
- No performance overhead

**Cons**:
- Cannot support long interactive sessions
- No reference resolution ("add stories to it")
- No big-picture awareness
- Risk of context overflow without warning
- Inefficient (repeated StateManager queries)

**Rejected because**: Core functionality (reference resolution, continuity) is impossible without context management. Risk of silent failures too high.

### Alternative 2: Simple LRU Cache Only

**Approach**: Keep last N operations in LRU cache, no checkpointing or optimization

**Pros**:
- Simple implementation (~200 lines)
- Low overhead
- Fast

**Cons**:
- No persistence across sessions
- No adaptive strategies for different context sizes
- No checkpoint/resume capability
- Cache eviction loses critical information
- No support for small contexts (4K-16K)

**Rejected because**: Insufficient for production use. Doesn't solve cross-session continuity or handle context limits safely.

### Alternative 3: External Memory Database (Vector DB)

**Approach**: Use vector database (Chroma, FAISS) for semantic search over all operations

**Pros**:
- Unlimited storage
- Semantic search capabilities
- Scales to millions of operations

**Cons**:
- High complexity (vector embeddings, database management)
- Latency (100-500ms per query)
- Requires embedding model (additional dependency)
- Overkill for most use cases
- Doesn't solve context window management (still need to limit what's loaded)

**Rejected because**: Over-engineered for requirements. Vector search not needed for recent operation recall. Adds latency without solving core problem.

### Alternative 4: Stateful LLM Service

**Approach**: Use stateful LLM service (like ChatGPT's conversation memory) managed by provider

**Pros**:
- Offloads complexity to provider
- Provider-optimized

**Cons**:
- Only works for cloud LLMs (not local Qwen)
- Vendor lock-in
- No control over optimization strategies
- Doesn't work offline
- May not support small context windows
- Privacy concerns (provider sees all context)

**Rejected because**: Obra is designed for local LLM orchestration. Vendor solutions don't align with architecture principles (local control, privacy, offline capability).

---

## Implementation Strategy

### Phase 1: Core Infrastructure (Weeks 1-2)
- Implement context window detection and configuration system
- Implement `ContextWindowManager` with adaptive thresholds
- Implement `WorkingMemory` with FIFO eviction
- Implement `ContextOptimizer` with 5 optimization techniques
- Implement `DecisionLogger` with ADR format
- Unit tests (≥90% coverage)

### Phase 2: Memory Tiers (Weeks 3-4)
- Implement `SessionMemoryManager` with compression
- Implement `EpisodicMemoryManager` with versioning
- Implement `CheckpointManager` with multi-trigger support
- Implement `AdaptiveOptimizer` with profile selection
- Unit tests (≥90% coverage)

### Phase 3: Integration (Weeks 5-6)
- Implement `OrchestratorContextManager` (coordinator)
- Integrate with `Orchestrator.execute_task()`
- Integrate with `Orchestrator.execute_nl_command()`
- Integrate with `NLCommandProcessor` for reference resolution
- Configuration schema updates (`config/models.yaml`)
- Integration tests

### Phase 4: Validation & Documentation (Weeks 7-8)
- Performance testing across context sizes (4K, 16K, 128K, 1M)
- Compression ratio validation
- Small context window testing (4K-32K)
- User documentation and guides
- Migration guide for existing deployments
- ADR finalization

**Total Timeline**: 8 weeks
**Risk Level**: Medium (new architecture, wide scope)
**Mitigation**: Phased rollout, comprehensive testing, backward compatibility

---

## Success Criteria

**Functional**:
- ✅ Context usage stays below 70% during normal operations
- ✅ Supports 4K to 1M+ context windows
- ✅ Reference resolution works ("add stories to it")
- ✅ Cross-session continuity maintained
- ✅ Auto-detection succeeds for 95% of deployments
- ✅ Manual override works when needed

**Non-Functional**:
- ✅ Context refresh latency <5s (P95)
- ✅ Memory overhead <100MB
- ✅ Compression ratio ≥0.7 (30% reduction)
- ✅ Zero context overflow errors in production
- ✅ Test coverage ≥90% for new components

**Small Context Window**:
- ✅ Works with 4K context (ultra-small local models)
- ✅ Adaptive strategies for 8K, 16K, 32K
- ✅ Checkpoint frequency appropriate for context size
- ✅ Graceful degradation when limits approached

---

## Assumptions

1. **Context window detection**: LLM APIs provide context window size (most do)
2. **Token estimation accuracy**: 4 chars/token heuristic ±10% accurate (industry standard)
3. **Compression effectiveness**: LLM can compress to 0.7 ratio (validated in PHASE_6)
4. **User acceptance**: Users accept <5s checkpoint latency
5. **Model stability**: Local LLMs (Qwen) remain stable and performant
6. **Configuration adoption**: Users will set `utilization_limit` if they want conservative usage

---

## References

- **LLM Development Agent Prompt Engineering Guide v2.2**: Industry best practices for context management, thresholds, optimization techniques
- **ADR-011**: Session Management Architecture (Implementer side)
- **ADR-017**: Unified Execution Architecture
- **CLAUDE.md**: Architecture Principles (#11 Session Management)
- **ORCHESTRATOR_CONTEXT_MANAGEMENT_DESIGN_V2.md**: Detailed design specification

---

## Notes

**Why Configurability Matters**:
- Local LLMs often have constrained contexts (4K-32K common)
- Users may prefer conservative limits (75% usage) for quality/safety
- Future models may have larger contexts (1M+)
- Detection may fail in some environments (manual override needed)

**Default Philosophy**:
- Auto-detect context window (works 95% of time)
- Use 100% of available context by default (utilization_limit=1.0)
- Adaptive optimization profiles based on detected size
- Conservative thresholds (50%, 70%, 85%) to prevent overflow

**Special Considerations for Small Contexts**:
- 4K-8K: Extremely aggressive optimization, frequent checkpoints, minimal history
- 8K-32K: Aggressive optimization, balanced checkpoints, moderate history
- Users with small contexts should expect more frequent checkpoints and less operation history

---

**Status**: Accepted
**Last Updated**: 2025-01-15
**Decision ID**: ADR-018
**Next Steps**: Proceed to implementation (see implementation guides)
