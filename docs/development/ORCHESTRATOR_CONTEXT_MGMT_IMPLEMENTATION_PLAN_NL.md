# Orchestrator Context Management - Implementation Plan (Natural Language)

**Document Type**: Implementation Plan (Human-Readable)
**Date**: 2025-01-15
**Related**: ADR-018 (Orchestrator Context Management)
**Target Audience**: Human developers, project managers
**Format**: Epic → Stories → Tasks breakdown

---

## Overview

This implementation plan provides a **human-readable** breakdown of the work required to implement the Orchestrator Context Management system (ADR-018). The work is organized following Obra's Agile/Scrum hierarchy: 1 Epic, 8 Stories, ~40 Tasks.

**Timeline**: 8 weeks (2 months)
**Team Size**: 1-2 developers
**Risk Level**: Medium
**Dependencies**: Existing StateManager, ContextManager, LLM interfaces

---

## Epic: Orchestrator Context Management System

**Epic ID**: EPIC-018
**Title**: Implement multi-tier memory architecture for Orchestrator LLM
**Description**: Build a comprehensive context window management system that enables the Orchestrator to maintain continuity across operations, support context windows from 4K to 1M+ tokens, and prevent context overflow through intelligent checkpointing and optimization.

**Business Value**:
- Enables long interactive sessions (50+ commands) without context overflow
- Supports reference resolution ("add stories to it")
- Provides cross-session project continuity
- Works with local LLMs (4K-32K contexts) and cloud LLMs (200K-1M+)
- Prevents silent failures from context limits

**Acceptance Criteria**:
- [ ] All 8 stories completed and tested
- [ ] Context usage stays below 70% during normal operations
- [ ] Supports 4K to 1M+ context windows
- [ ] Reference resolution works in NL commands
- [ ] Auto-detection succeeds for 95% of deployments
- [ ] Test coverage ≥90% for new components
- [ ] Documentation complete (ADR, user guides, API docs)

**Estimated Effort**: 8 weeks

---

## Story 1: Context Window Detection & Configuration System

**Story ID**: STORY-018-1
**Epic**: EPIC-018
**Title**: Build configurable context window detection system
**Description**: As a developer, I want the Orchestrator to automatically detect LLM context window size and support manual configuration, so that it works across different models (4K-1M+) without hardcoding.

**User Story**: As an Obra user, I want the system to automatically detect my LLM's context window size, so that I don't have to manually configure it for each model.

**Acceptance Criteria**:
- [ ] `config/models.yaml` schema supports context window definitions
- [ ] Auto-detection queries LLM for max context (if supported)
- [ ] Manual override works when auto-detection fails
- [ ] Utilization limit configurable (e.g., 75% of available)
- [ ] Fallback to conservative 16K if detection fails
- [ ] Works with Ollama, Anthropic, OpenAI providers
- [ ] Unit tests: ≥90% coverage

**Tasks**:

### Task 1.1: Design `config/models.yaml` Schema
**Estimate**: 4 hours
**Description**: Design YAML schema for LLM model definitions including context window, provider, costs, etc.
**Deliverables**:
- `config/models.yaml.example` with sample definitions
- Schema validation logic
- Documentation of schema fields

### Task 1.2: Implement Model Configuration Loader
**Estimate**: 8 hours
**Description**: Implement `ModelConfigLoader` class to load and validate model configurations
**Deliverables**:
- `src/core/model_config_loader.py`
- Load from YAML, validate schema
- Error handling for missing/invalid configs
- Unit tests

### Task 1.3: Implement Context Window Auto-Detection
**Estimate**: 16 hours
**Description**: Implement auto-detection of context window size from LLM provider
**Deliverables**:
- `src/orchestration/memory/context_window_detector.py`
- Query Ollama API for model info
- Query Anthropic/OpenAI for model capabilities
- Fallback to configured value if API unavailable
- Unit tests with mocked API calls

### Task 1.4: Implement Utilization Limit Logic
**Estimate**: 8 hours
**Description**: Allow users to limit context usage to percentage of available (e.g., 75%)
**Deliverables**:
- Logic in `ContextWindowManager` to apply utilization limit
- Effective max = configured max × utilization_limit
- Configuration options in `config/default_config.yaml`
- Unit tests

### Task 1.5: Integration Tests for Configuration System
**Estimate**: 8 hours
**Description**: End-to-end tests for model loading and context detection
**Deliverables**:
- Integration tests with real config files
- Test multiple models (4K, 16K, 128K, 200K)
- Test auto-detection success/failure paths
- Test utilization limit calculations

**Story Estimate**: 44 hours (~1 week)

---

## Story 2: Context Window Manager & Threshold System

**Story ID**: STORY-018-2
**Epic**: EPIC-018
**Title**: Implement adaptive context window manager with industry-standard thresholds
**Description**: As a developer, I want a context window manager that tracks token usage and triggers actions at industry-standard thresholds (50%, 70%, 85%), adapting to any context size.

**User Story**: As an Obra user, I want the system to warn me when approaching context limits and automatically checkpoint before overflow, so that I never lose work to context overflow.

**Acceptance Criteria**:
- [ ] Tracks cumulative token usage across operations
- [ ] Thresholds at 50% (green), 70% (yellow), 85% (orange), 95% (red)
- [ ] Thresholds calculated as percentages (works with any context size)
- [ ] Provides zone status (green/yellow/orange/red)
- [ ] Recommends actions per zone
- [ ] Thread-safe for concurrent operations
- [ ] Unit tests: ≥90% coverage

**Tasks**:

### Task 2.1: Implement ContextWindowManager Core
**Estimate**: 12 hours
**Description**: Build core context window tracking with dynamic thresholds
**Deliverables**:
- `src/orchestration/memory/context_window_manager.py`
- Track used_tokens, calculate percentages
- Dynamic threshold calculation from config
- Zone determination (green/yellow/orange/red)
- Thread-safe with RLock

### Task 2.2: Implement Adaptive Threshold Calculation
**Estimate**: 8 hours
**Description**: Calculate absolute token thresholds from percentages
**Deliverables**:
- Method to convert 50%, 70%, 85% to absolute tokens
- Works with 4K to 1M+ contexts
- Update thresholds when context size changes
- Unit tests for various context sizes

### Task 2.3: Implement Action Recommendation System
**Estimate**: 4 hours
**Description**: Recommend actions based on current zone
**Deliverables**:
- Action mapping (green → proceed, yellow → monitor, etc.)
- Method: `get_recommended_action()`
- Logging of zone transitions
- Unit tests

### Task 2.4: Implement Token Usage Tracking
**Estimate**: 8 hours
**Description**: Track token usage across operations with overflow detection
**Deliverables**:
- Method: `add_usage(tokens)` with overflow checks
- Method: `used_tokens()`, `available_tokens()`, `usage_percentage()`
- Warning logs at threshold crossings
- Reset capability for checkpoints
- Unit tests

### Task 2.5: Unit Tests for ContextWindowManager
**Estimate**: 12 hours
**Description**: Comprehensive unit tests for all threshold scenarios
**Deliverables**:
- Test suite with ≥90% coverage
- Test all zones (green/yellow/orange/red)
- Test threshold calculations (4K, 16K, 128K, 1M contexts)
- Test concurrent access (thread safety)
- Test overflow scenarios

**Story Estimate**: 44 hours (~1 week)

---

## Story 3: Working Memory (Tier 1)

**Story ID**: STORY-018-3
**Epic**: EPIC-018
**Title**: Implement in-process working memory with adaptive sizing
**Description**: As a developer, I want a fast in-memory cache for recent operations that adapts size based on context window (10 ops for 4K, 100 ops for 1M).

**User Story**: As an Obra user, I want the Orchestrator to remember my last few commands, so that it can resolve references like "add 3 stories to it" without asking what "it" means.

**Acceptance Criteria**:
- [ ] FIFO eviction when at capacity
- [ ] Adaptive max operations (10 for 4K, 30 for 16K, 50 for 128K, 100 for 1M)
- [ ] Fast access (<10ms per query)
- [ ] Thread-safe
- [ ] Token budget: 5-10% of context window
- [ ] Unit tests: ≥90% coverage

**Tasks**:

### Task 3.1: Implement WorkingMemory Core
**Estimate**: 12 hours
**Description**: Build in-memory FIFO cache for operations
**Deliverables**:
- `src/orchestration/memory/working_memory.py`
- Use `collections.deque` for FIFO
- Track current tokens used
- Add/retrieve operations
- Thread-safe with RLock

### Task 3.2: Implement Adaptive Sizing Logic
**Estimate**: 8 hours
**Description**: Automatically size working memory based on context window
**Deliverables**:
- Calculate max_operations from context size
- 4K → 10 ops, 16K → 30 ops, 128K → 50 ops, 1M → 100 ops
- Calculate max_tokens (5-10% of context)
- Configuration overrides
- Unit tests

### Task 3.3: Implement Query Interface
**Estimate**: 8 hours
**Description**: Methods for querying recent operations
**Deliverables**:
- `get_recent_operations(limit)` - most recent first
- `get_operations(operation_type, limit)` - filter by type
- `search(query)` - keyword search
- Unit tests

### Task 3.4: Implement Eviction Logic
**Estimate**: 8 hours
**Description**: FIFO eviction when capacity exceeded
**Deliverables**:
- Auto-evict when max_operations exceeded
- Auto-evict when max_tokens exceeded
- Track eviction stats
- Logging of evictions
- Unit tests

### Task 3.5: Unit Tests for WorkingMemory
**Estimate**: 12 hours
**Description**: Comprehensive tests for all scenarios
**Deliverables**:
- Test FIFO eviction
- Test adaptive sizing (4K, 16K, 128K, 1M)
- Test query methods
- Test thread safety
- Test token budget adherence
- ≥90% coverage

**Story Estimate**: 48 hours (~1 week)

---

## Story 4: Context Optimization Techniques

**Story ID**: STORY-018-4
**Epic**: EPIC-018
**Title**: Implement 5 industry-standard context optimization techniques
**Description**: As a developer, I want automated context optimization using summarization, artifact registry, differential state, external storage, and pruning, so that context stays within limits.

**User Story**: As an Obra user, I want the system to automatically compress old information when approaching context limits, so that I can work on large projects without manual intervention.

**Acceptance Criteria**:
- [ ] Summarization: Compress completed phases to ≤500 tokens
- [ ] Artifact Registry: File → summary mappings
- [ ] Differential State: Store only changes since checkpoint
- [ ] External Storage: Move large data (>2000 tokens) to files
- [ ] Pruning: Remove debug traces >1hr, keep last 5 validations
- [ ] Compression ratio ≥0.7 (30% reduction)
- [ ] Unit tests: ≥90% coverage

**Tasks**:

### Task 4.1: Implement ContextOptimizer Base
**Estimate**: 8 hours
**Description**: Build optimizer coordinator that applies all techniques
**Deliverables**:
- `src/orchestration/memory/context_optimizer.py`
- Orchestrate all 5 optimization techniques
- Track optimization metrics (before/after tokens)
- Unit tests

### Task 4.2: Implement Summarization Technique
**Estimate**: 16 hours
**Description**: Compress completed phases using LLM summarization
**Deliverables**:
- Method: `_summarize_completed_phases(context)`
- Use LLM to compress to target tokens (500 for large, 100 for small contexts)
- Preserve key accomplishments, decisions, issues
- Save full data externally
- Unit tests with mocked LLM

### Task 4.3: Implement Artifact Registry Technique
**Estimate**: 12 hours
**Description**: Replace full file contents with file → summary mappings
**Deliverables**:
- Method: `_apply_artifact_registry(context)`
- Create file_path → {summary, last_modified, size} mapping
- Remove full file contents from context
- Unit tests

### Task 4.4: Implement Differential State Technique
**Estimate**: 16 hours
**Description**: Store only changes since last checkpoint
**Deliverables**:
- Method: `_convert_to_differential_state(context)`
- Compute diff between current state and last checkpoint
- Store base_checkpoint_id + delta
- Unit tests with state diffs

### Task 4.5: Implement External Storage Technique
**Estimate**: 12 hours
**Description**: Move large artifacts (>2000 tokens) to files
**Deliverables**:
- Method: `_externalize_large_artifacts(context)`
- Move data >2000 tokens to `.obra/memory/artifacts/`
- Replace with {_external_ref, _summary, _tokens}
- File I/O with error handling
- Unit tests

### Task 4.6: Implement Pruning Technique
**Estimate**: 12 hours
**Description**: Remove temporary/stale data
**Deliverables**:
- Method: `_prune_temporary_data(context)`
- Remove debug traces >1hr old
- Keep only last 5 validation results
- Keep unresolved errors + last 10 resolved
- Unit tests

### Task 4.7: Integration Tests for Optimization
**Estimate**: 12 hours
**Description**: End-to-end optimization tests
**Deliverables**:
- Test full optimization pipeline
- Verify compression ratio ≥0.7
- Test with various context sizes
- Test preservation of critical data
- ≥90% coverage

**Story Estimate**: 88 hours (~2 weeks)

---

## Story 5: Adaptive Optimization Profiles

**Story ID**: STORY-018-5
**Epic**: EPIC-018
**Title**: Implement adaptive optimization profiles for different context sizes
**Description**: As a developer, I want optimization strategies that adapt to context window size (ultra-aggressive for 4K, minimal for 1M+), so that small and large contexts are handled appropriately.

**User Story**: As an Obra user with a 4K local LLM, I want aggressive optimization so I can still work on projects, even though my context is very limited.

**Acceptance Criteria**:
- [ ] 5 profiles: ultra-aggressive, aggressive, balanced-aggressive, balanced, minimal
- [ ] Auto-selection based on context window size
- [ ] Configurable thresholds per profile
- [ ] Manual override supported
- [ ] Unit tests: ≥90% coverage

**Tasks**:

### Task 5.1: Design Optimization Profile Schema
**Estimate**: 4 hours
**Description**: Define profile structure and thresholds
**Deliverables**:
- Profile definitions (JSON/YAML)
- Thresholds for each profile (summarization, checkpoint interval, etc.)
- Documentation

### Task 5.2: Implement AdaptiveOptimizer
**Estimate**: 12 hours
**Description**: Build profile selector and applicator
**Deliverables**:
- `src/orchestration/memory/adaptive_optimizer.py`
- Auto-select profile based on context size
- Apply profile thresholds
- Manual override support
- Unit tests

### Task 5.3: Implement Profile-Specific Optimizations
**Estimate**: 16 hours
**Description**: Implement optimization logic for each profile
**Deliverables**:
- Ultra-aggressive: summarize >100 tokens, checkpoint every 30 min
- Aggressive: summarize >300 tokens, checkpoint every 1 hour
- Balanced-aggressive: summarize >500 tokens, checkpoint every 2 hours
- Balanced: summarize >500 tokens, checkpoint every 4 hours
- Minimal: summarize >1000 tokens, checkpoint every 8 hours
- Unit tests for each profile

### Task 5.4: Integration with ContextWindowManager
**Estimate**: 8 hours
**Description**: Connect adaptive profiles to context window manager
**Deliverables**:
- Pass detected context size to AdaptiveOptimizer
- Apply selected profile thresholds
- Log profile selection
- Integration tests

### Task 5.5: Configuration and Override System
**Estimate**: 8 hours
**Description**: Allow manual profile override in config
**Deliverables**:
- Config option: `optimization_profile: null | ultra-aggressive | aggressive | ...`
- Override auto-selection if specified
- Validation of manual overrides
- Unit tests

**Story Estimate**: 48 hours (~1 week)

---

## Story 6: Session & Episodic Memory (Tiers 2-3)

**Story ID**: STORY-018-6
**Epic**: EPIC-018
**Title**: Implement session and episodic memory with compression and versioning
**Description**: As a developer, I want document-based memory tiers for session narratives and long-term project state, with automatic compression and versioning.

**User Story**: As an Obra user, I want the system to remember what happened in my session and preserve project state across sessions, so that I can pick up where I left off.

**Acceptance Criteria**:
- [ ] Session memory: Chronological narrative with compression at 40K tokens
- [ ] Episodic memory: project_state.md, work_plan.md, decision_log.md
- [ ] Compression maintains ≥0.7 ratio
- [ ] Versioning preserves history (last 10 versions)
- [ ] Graceful session flush and archive
- [ ] Unit tests: ≥90% coverage

**Tasks**:

### Task 6.1: Implement SessionMemoryManager
**Estimate**: 20 hours
**Description**: Build session-scoped memory with compression
**Deliverables**:
- `src/orchestration/memory/session_memory_manager.py`
- Append operations to session document
- Compress when >40K tokens
- Generate session summary
- Archive on session end
- Unit tests

### Task 6.2: Implement EpisodicMemoryManager
**Estimate**: 20 hours
**Description**: Build long-term memory documents
**Deliverables**:
- `src/orchestration/memory/episodic_memory_manager.py`
- Manage project_state.md, work_plan.md, decision_log.md
- Version documents before updates
- Compress when >30K tokens
- Integration with session summaries
- Unit tests

### Task 6.3: Implement Document Compression
**Estimate**: 16 hours
**Description**: LLM-based compression for session and episodic docs
**Deliverables**:
- Method: `compress_document(doc, target_ratio)`
- Use LLM for intelligent summarization
- Preserve critical information (decisions, issues)
- Achieve ≥0.7 compression ratio
- Unit tests with mocked LLM

### Task 6.4: Implement Versioning System
**Estimate**: 12 hours
**Description**: Version documents before modification
**Deliverables**:
- Method: `_version_document(doc_path)`
- Save to `.obra/memory/versions/` with timestamp
- Keep last N versions (configurable, default 10)
- Cleanup old versions
- Unit tests

### Task 6.5: Integration Tests for Memory Tiers
**Estimate**: 16 hours
**Description**: End-to-end tests for session and episodic memory
**Deliverables**:
- Test session lifecycle (create, append, compress, archive)
- Test episodic updates and versioning
- Test compression ratios
- Test cross-session continuity
- ≥90% coverage

**Story Estimate**: 84 hours (~2 weeks)

---

## Story 7: Checkpoint System with Multi-Trigger Support

**Story ID**: STORY-018-7
**Epic**: EPIC-018
**Title**: Implement checkpoint system with threshold, time, and operation-count triggers
**Description**: As a developer, I want a checkpoint system that triggers on thresholds (70%, 85%), time intervals (4 hours adaptive), and operation counts (100 adaptive), with structured checkpoint format.

**User Story**: As an Obra user, I want my work automatically saved at checkpoints, so that I never lose progress if the system crashes or I need to restart.

**Acceptance Criteria**:
- [ ] Threshold triggers: 70% (yellow), 85% (orange)
- [ ] Time trigger: Configurable interval (adaptive: 30min for 4K, 4hr for 128K, 8hr for 1M)
- [ ] Operation count trigger: Configurable (adaptive: 20 for 4K, 100 for 128K, 200 for 1M)
- [ ] Structured checkpoint format with resume instructions
- [ ] Checkpoint save/load/resume functionality
- [ ] Unit tests: ≥90% coverage

**Tasks**:

### Task 7.1: Design Checkpoint Schema
**Estimate**: 4 hours
**Description**: Define structured checkpoint format (JSON)
**Deliverables**:
- Checkpoint schema (id, timestamp, trigger, context_snapshot, resume_instructions, metadata)
- Example checkpoint files
- Documentation

### Task 7.2: Implement CheckpointManager Core
**Estimate**: 16 hours
**Description**: Build checkpoint creation and management
**Deliverables**:
- `src/orchestration/memory/checkpoint_manager.py`
- Create checkpoints with structured format
- Save to `.obra/checkpoints/`
- Load checkpoints
- Unit tests

### Task 7.3: Implement Multi-Trigger Logic
**Estimate**: 16 hours
**Description**: Support threshold, time, and operation-count triggers
**Deliverables**:
- Method: `should_checkpoint(usage_pct)` with all trigger checks
- Threshold-based: 70%, 85%
- Time-based: Hours since last checkpoint
- Operation-count: Operations since last checkpoint
- Adaptive intervals based on context size
- Unit tests for all trigger types

### Task 7.4: Implement Checkpoint Resume
**Estimate**: 12 hours
**Description**: Restore Orchestrator state from checkpoint
**Deliverables**:
- Method: `resume_from_checkpoint(checkpoint_id)`
- Load context snapshot artifacts
- Restore working memory state
- Follow resume instructions
- Unit tests

### Task 7.5: Integration Tests for Checkpointing
**Estimate**: 16 hours
**Description**: End-to-end checkpoint lifecycle tests
**Deliverables**:
- Test checkpoint creation (all triggers)
- Test checkpoint resume
- Test checkpoint with different context sizes
- Test checkpoint failure recovery
- ≥90% coverage

**Story Estimate**: 64 hours (~1.5 weeks)

---

## Story 8: Integration & Orchestrator Coordination

**Story ID**: STORY-018-8
**Epic**: EPIC-018
**Title**: Integrate all components into OrchestratorContextManager and wire to Orchestrator
**Description**: As a developer, I want all memory components coordinated by OrchestratorContextManager and integrated with Orchestrator.execute_task() and execute_nl_command(), enabling full context management.

**User Story**: As an Obra user, I want context management to work automatically whenever I execute tasks or NL commands, without needing to think about it.

**Acceptance Criteria**:
- [ ] OrchestratorContextManager coordinates all tiers
- [ ] Integrated with Orchestrator.execute_task()
- [ ] Integrated with Orchestrator.execute_nl_command()
- [ ] Integrated with NLCommandProcessor for reference resolution
- [ ] Configuration loaded from config files
- [ ] Integration tests pass
- [ ] Test coverage ≥90%

**Tasks**:

### Task 8.1: Implement OrchestratorContextManager Coordinator
**Estimate**: 24 hours
**Description**: Build central coordinator for all memory components
**Deliverables**:
- `src/orchestration/orchestrator_context_manager.py`
- Initialize all components (WorkingMemory, SessionMemory, EpisodicMemory, etc.)
- Coordinate context building across tiers
- Handle checkpoint triggers and execution
- Track context usage
- Unit tests

### Task 8.2: Integrate with Orchestrator.execute_task()
**Estimate**: 16 hours
**Description**: Add context tracking to task execution
**Deliverables**:
- Modifications to `src/orchestrator.py`
- Record operation before/after task execution
- Build Orchestrator context for operation
- Trigger checkpoint if needed
- Integration tests

### Task 8.3: Integrate with Orchestrator.execute_nl_command()
**Estimate**: 16 hours
**Description**: Add context tracking to NL command execution
**Deliverables**:
- Modifications to `src/orchestrator.py`
- Record NL command operation
- Build Orchestrator context
- Trigger checkpoint if needed
- Integration tests

### Task 8.4: Integrate with NLCommandProcessor for Reference Resolution
**Estimate**: 16 hours
**Description**: Enable "it", "that" reference resolution using recent operations
**Deliverables**:
- Modifications to `src/nl/nl_command_processor.py`
- Query recent operations for pronoun resolution
- Context-aware entity extraction
- Integration tests with reference examples

### Task 8.5: Configuration Loading and Validation
**Estimate**: 12 hours
**Description**: Load model configs and orchestrator configs
**Deliverables**:
- Load `config/models.yaml` and `config/default_config.yaml`
- Validate configurations
- Apply defaults
- Error handling for invalid configs
- Unit tests

### Task 8.6: End-to-End Integration Tests
**Estimate**: 24 hours
**Description**: Comprehensive integration tests for full system
**Deliverables**:
- Test full task execution with context tracking
- Test full NL command with reference resolution
- Test checkpoint triggers during execution
- Test cross-session continuity
- Test with different context sizes (4K, 16K, 128K, 200K)
- ≥90% coverage

**Story Estimate**: 108 hours (~2.5 weeks)

---

## Testing & Documentation (Cross-Story)

### Performance Testing
**Estimate**: 16 hours
**Deliverables**:
- Measure context refresh latency (target <5s P95)
- Measure memory overhead (target <100MB)
- Measure compression ratios (target ≥0.7)
- Test with varying context sizes (4K to 1M)
- Performance report

### Small Context Window Validation
**Estimate**: 16 hours
**Deliverables**:
- Test with 4K context (phi-3-mini)
- Test with 8K context (qwen 3b)
- Test with 16K context (qwen 7b)
- Verify adaptive strategies work correctly
- Validate checkpoint frequencies

### Documentation
**Estimate**: 24 hours
**Deliverables**:
- User guide: "Orchestrator Context Management Guide"
- Developer guide: "Context Management Architecture"
- Configuration reference
- Migration guide for existing deployments
- API documentation (docstrings)

### Migration & Rollout
**Estimate**: 16 hours
**Deliverables**:
- Backward compatibility verification
- Migration script for existing sessions
- Rollout plan (feature flag, phased deployment)
- Rollback plan

---

## Summary

**Total Epic Effort**: ~520 hours (~13 weeks at 40 hrs/week)

**Story Breakdown**:
1. Context Window Detection & Config: 44 hours (~1 week)
2. Context Window Manager & Thresholds: 44 hours (~1 week)
3. Working Memory (Tier 1): 48 hours (~1 week)
4. Context Optimization Techniques: 88 hours (~2 weeks)
5. Adaptive Optimization Profiles: 48 hours (~1 week)
6. Session & Episodic Memory: 84 hours (~2 weeks)
7. Checkpoint System: 64 hours (~1.5 weeks)
8. Integration & Coordination: 108 hours (~2.5 weeks)
9. Testing & Documentation: 72 hours (~1.5 weeks)

**Timeline**:
- **With 1 developer**: ~13 weeks (3 months)
- **With 2 developers**: ~8 weeks (2 months) - accounting for coordination overhead

**Risk Mitigation**:
- Start with Stories 1-3 (foundational, low risk)
- Stories 4-5 can run in parallel after 1-3 complete
- Story 6 (memory tiers) depends on Story 4 (optimization)
- Story 7 (checkpoints) can develop in parallel with Story 6
- Story 8 (integration) is final, depends on all others

**Success Tracking**:
- Daily standups to track progress
- Weekly demos of completed stories
- Continuous integration tests (run on every commit)
- Code reviews for all changes
- Documentation updates alongside code

---

**Next Steps**:
1. Review and approve implementation plan
2. Create tasks in project management system (if applicable)
3. Assign developers to stories
4. Begin Story 1 (Context Window Detection & Config)
5. Set up CI/CD for continuous testing

**Related Documents**:
- ADR-018: Orchestrator Context Management
- Machine-Optimized Implementation Plan: For Claude Code execution
- Small Context Window Quick Reference: For 4K-32K deployments
