# Orchestrator Context Management System - Design Proposal

**Document Type**: Architecture Design Proposal
**Status**: Draft for Review
**Date**: 2025-01-15
**Author**: System Architecture Analysis
**Purpose**: Design comprehensive context window management for the Orchestrator LLM

---

## Executive Summary

This document proposes a multi-tier memory architecture for the Orchestrator (local Qwen LLM) to manage its own context window across operations. Currently, the Orchestrator builds context from scratch for each operation with no persistent memory, limiting its ability to maintain continuity and big-picture awareness in long-running projects.

**Key Objectives**:
1. **Track Orchestrator's own context usage** across operations (separate from Implementer sessions)
2. **Maintain continuity documents** that preserve project state without context bloat
3. **Implement intelligent refresh strategies** when approaching context limits
4. **Enable big-picture awareness** through hierarchical memory tiers
5. **Prevent document bloat** through compression, summarization, and archival
6. **Support graceful degradation** when context limits are reached

**Success Metrics**:
- Context window utilization stays below 80% during normal operations
- Orchestrator maintains awareness of last 50+ operations without manual intervention
- Document size growth is sub-linear (compression ratio ≥0.7)
- Context refresh latency <5 seconds (P95)

---

## 1. Problem Statement

### 1.1 Current Limitations

**Stateless Operation Model**:
```
User Command/Task → Query StateManager → Build Context → LLM Call → Discard Context
```

**Issues**:
- No memory of recent operations (can't answer "what did we just do?")
- Rebuilds context from database every time (inefficient)
- Loses "big picture" awareness over long sessions
- Cannot track own context window usage
- No refresh strategy when working on large projects
- Relies entirely on StateManager queries (database overhead)

### 1.2 Specific Scenarios Where This Fails

**Scenario 1: Long Interactive Session**
```
User: "Create epic for authentication"
[Orch creates epic, forgets immediately]

User: "Add 3 stories to it"
[Orch asks: "To which epic?" - no memory of previous command]
```

**Scenario 2: Complex Project Over Multiple Sessions**
```
Session 1: Work on Epic 1-5 (20 tasks completed)
Session 2: Continue Epic 6
[Orch has no awareness of what was accomplished in Session 1]
```

**Scenario 3: Context Window Overflow**
```
Large project: 50 epics, 200 stories, 1000 tasks
Orch tries to load all context → exceeds 128K token limit → crashes or truncates critical info
```

### 1.3 Requirements

**Functional Requirements**:
- FR1: Track Orchestrator's context window usage in real-time
- FR2: Maintain persistent memory across operations within a session
- FR3: Preserve critical context across sessions (days/weeks)
- FR4: Automatically refresh context when approaching limits
- FR5: Provide "big picture" project awareness without loading all data
- FR6: Support natural language queries about recent operations

**Non-Functional Requirements**:
- NFR1: Context refresh latency <5s (P95)
- NFR2: Memory overhead <100MB for typical project
- NFR3: Document compression ratio ≥0.7 (30% size reduction)
- NFR4: Support projects with 1000+ tasks
- NFR5: Graceful degradation when context limits hit
- NFR6: Thread-safe for concurrent operations

---

## 2. Proposed Architecture

### 2.1 Multi-Tier Memory System

Inspired by human memory architecture (working, episodic, semantic):

```
┌──────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR MEMORY TIERS                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Tier 1: WORKING MEMORY (In-Process, Fast)                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ - Recent operations (last 20-50)                       │     │
│  │ - Active decision chain                                │     │
│  │ - Current context window usage                         │     │
│  │ - Session metadata                                     │     │
│  │ Lifespan: Current session only                         │     │
│  │ Size: ~5-10K tokens                                    │     │
│  └────────────────────────────────────────────────────────┘     │
│                           ↓ (flush on 80% full or session end)   │
│                                                                   │
│  Tier 2: SESSION MEMORY (Documents, Medium-term)                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Files: .obra/sessions/session_<id>.md                  │     │
│  │ - Session log (chronological narrative)                │     │
│  │ - Decisions made this session                          │     │
│  │ - Issues encountered                                   │     │
│  │ Lifespan: Until session end, then summarized           │     │
│  │ Size: ~20-50K tokens (auto-compress at 40K)            │     │
│  └────────────────────────────────────────────────────────┘     │
│                           ↓ (summarize on session end)            │
│                                                                   │
│  Tier 3: EPISODIC MEMORY (Project History, Long-term)            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Files: .obra/memory/project_state.md                   │     │
│  │        .obra/memory/work_plan.md                       │     │
│  │        .obra/memory/decision_log.md                    │     │
│  │ - Project current state (snapshot)                     │     │
│  │ - Work plan (what's next)                              │     │
│  │ - Decision history (compressed)                        │     │
│  │ Lifespan: Project lifetime                             │     │
│  │ Size: 10-30K tokens each (periodic compression)        │     │
│  └────────────────────────────────────────────────────────┘     │
│                           ↓ (query as needed)                     │
│                                                                   │
│  Tier 4: SEMANTIC MEMORY (Database, Queryable)                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ StateManager: Tasks, Epics, Stories, Milestones        │     │
│  │ - Structured data (existing system)                    │     │
│  │ - Always authoritative source                          │     │
│  │ Lifespan: Permanent                                    │     │
│  │ Size: Unbounded (database)                             │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestrator                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           OrchestratorContextManager (NEW)               │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ WorkingMemory          - In-process cache          │  │  │
│  │  │ SessionMemoryManager   - Session documents         │  │  │
│  │  │ EpisodicMemoryManager  - Project history docs      │  │  │
│  │  │ ContextWindowTracker   - Token usage monitoring    │  │  │
│  │  │ MemoryCompressor       - Summarization/compression │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ↓ ↑                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Existing Components (Integration Points)               │  │
│  │  - StateManager (database queries)                      │  │
│  │  - ContextManager (prompt building, summarization)      │  │
│  │  - NLCommandProcessor (operation tracking)              │  │
│  │  - DecisionEngine (decision logging)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Design

### 3.1 OrchestratorContextManager (Core Orchestration)

**Purpose**: Central coordinator for all Orchestrator memory tiers

**Location**: `src/orchestration/orchestrator_context_manager.py`

**Interface**:
```python
class OrchestratorContextManager:
    """Manage Orchestrator's multi-tier memory system.

    Responsibilities:
    - Track context window usage across operations
    - Coordinate memory tier interactions
    - Trigger refresh/compression when needed
    - Provide unified context retrieval

    Thread-safe for concurrent operations.
    """

    def __init__(
        self,
        state_manager: StateManager,
        context_builder: ContextManager,
        llm_interface: LocalLLMInterface,
        config: Dict[str, Any]
    ):
        """Initialize context manager.

        Args:
            state_manager: StateManager for database queries
            context_builder: ContextManager for prompt building/summarization
            llm_interface: LLM for summarization operations
            config: Configuration dictionary
        """
        # Memory tier components
        self.working_memory = WorkingMemory(config)
        self.session_memory = SessionMemoryManager(config, llm_interface)
        self.episodic_memory = EpisodicMemoryManager(config, llm_interface)

        # Context window tracking
        self.context_tracker = ContextWindowTracker(
            max_tokens=config.get('orchestrator.context_window', 128000),
            warning_threshold=0.70,
            refresh_threshold=0.80,
            critical_threshold=0.95
        )

        # Compression utilities
        self.compressor = MemoryCompressor(context_builder, llm_interface)

        # Thread safety
        self._lock = RLock()

    # === Core Operations ===

    def record_operation(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        tokens_used: int
    ) -> None:
        """Record an operation in working memory.

        Args:
            operation_type: Type of operation (nl_command, task_execution, etc.)
            operation_data: Operation details
            tokens_used: Tokens consumed by this operation

        Side Effects:
            - Updates working memory
            - Updates context window usage
            - May trigger refresh if threshold exceeded
        """
        with self._lock:
            # Add to working memory
            self.working_memory.add_operation({
                'type': operation_type,
                'data': operation_data,
                'timestamp': datetime.now(UTC),
                'tokens': tokens_used
            })

            # Update context tracker
            self.context_tracker.add_usage(tokens_used)

            # Check if refresh needed
            if self.context_tracker.should_refresh():
                self._trigger_refresh()

    def get_orchestrator_context(
        self,
        for_operation: str,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build context for Orchestrator's current operation.

        Intelligently combines context from all tiers to stay within token budget.

        Args:
            for_operation: Operation type (validation, decision, nl_command, etc.)
            max_tokens: Optional token budget override

        Returns:
            Dictionary with context from all tiers:
            {
                'working_memory': {...},      # Recent operations
                'session_summary': "...",     # Current session narrative
                'project_state': "...",       # Current project snapshot
                'work_plan': "...",          # What's next
                'recent_decisions': [...]     # Decision history
            }
        """
        with self._lock:
            max_tokens = max_tokens or self.context_tracker.available_tokens()

            # Token allocation strategy (priority order)
            allocation = {
                'working_memory': int(max_tokens * 0.3),    # 30% - most recent
                'session_summary': int(max_tokens * 0.2),   # 20% - current session
                'project_state': int(max_tokens * 0.25),    # 25% - canonical state
                'work_plan': int(max_tokens * 0.15),        # 15% - what's next
                'decision_history': int(max_tokens * 0.10)  # 10% - why decisions made
            }

            context = {}

            # Tier 1: Working memory (always included, most recent)
            context['working_memory'] = self.working_memory.get_recent_operations(
                limit=allocation['working_memory']
            )

            # Tier 2: Session memory (current session narrative)
            context['session_summary'] = self.session_memory.get_summary(
                max_tokens=allocation['session_summary']
            )

            # Tier 3: Episodic memory (project state, work plan, decisions)
            context['project_state'] = self.episodic_memory.get_project_state(
                max_tokens=allocation['project_state']
            )
            context['work_plan'] = self.episodic_memory.get_work_plan(
                max_tokens=allocation['work_plan']
            )
            context['decision_history'] = self.episodic_memory.get_recent_decisions(
                max_tokens=allocation['decision_history']
            )

            return context

    def flush_session(self) -> str:
        """Flush current session to episodic memory.

        Called at session end (graceful shutdown, timeout, or manual flush).

        Returns:
            Path to session archive

        Side Effects:
            - Summarizes session memory
            - Archives session document
            - Updates episodic memory (project_state, work_plan)
            - Clears working memory
            - Resets context tracker
        """
        with self._lock:
            # Generate session summary
            session_summary = self.session_memory.generate_summary()

            # Archive session document
            archive_path = self.session_memory.archive()

            # Update episodic memory with session insights
            self.episodic_memory.integrate_session(session_summary)

            # Clear working memory
            self.working_memory.clear()

            # Reset context tracker
            self.context_tracker.reset()

            logger.info(f"Session flushed to {archive_path}")
            return archive_path

    def _trigger_refresh(self) -> None:
        """Trigger context refresh when threshold exceeded.

        Refresh strategy:
        1. Flush working memory to session memory
        2. Compress session memory if needed
        3. Update episodic memory
        4. Reset context tracker

        Should complete in <5 seconds (NFR1).
        """
        logger.info(f"Context refresh triggered at {self.context_tracker.usage_percentage():.1f}%")

        # Flush working memory to session document
        self.session_memory.append_operations(
            self.working_memory.get_all_operations()
        )
        self.working_memory.clear()

        # Compress session memory if large
        if self.session_memory.token_count() > 40000:
            self.session_memory.compress()

        # Update episodic memory with latest state
        self.episodic_memory.update_project_state(
            self.session_memory.get_current_state()
        )

        # Reset tracker to free space
        self.context_tracker.reset()

        logger.info("Context refresh complete")

    # === Query Interface ===

    def query_recent_operations(
        self,
        operation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Query recent operations from working memory.

        Enables natural language queries like:
        - "What did we just do?"
        - "What was the last task executed?"
        - "Show me recent NL commands"
        """
        return self.working_memory.get_operations(
            operation_type=operation_type,
            limit=limit
        )

    def search_memory(self, query: str, max_results: int = 5) -> List[str]:
        """Search across all memory tiers.

        Uses semantic search (keyword matching initially, embeddings future).
        """
        results = []

        # Search working memory
        results.extend(
            self.working_memory.search(query, max_results=max_results)
        )

        # Search session memory
        results.extend(
            self.session_memory.search(query, max_results=max_results)
        )

        # Search episodic memory
        results.extend(
            self.episodic_memory.search(query, max_results=max_results)
        )

        # Rank and return top results
        return self._rank_search_results(results)[:max_results]

    # === Statistics ===

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        return {
            'context_window': {
                'used_tokens': self.context_tracker.used_tokens(),
                'available_tokens': self.context_tracker.available_tokens(),
                'usage_percentage': self.context_tracker.usage_percentage(),
                'refresh_count': self.context_tracker.refresh_count
            },
            'working_memory': self.working_memory.get_stats(),
            'session_memory': self.session_memory.get_stats(),
            'episodic_memory': self.episodic_memory.get_stats()
        }
```

---

### 3.2 WorkingMemory (Tier 1 - In-Process)

**Purpose**: Fast, ephemeral storage for most recent operations

**Location**: `src/orchestration/memory/working_memory.py`

**Design**:
```python
class WorkingMemory:
    """In-process cache for recent Orchestrator operations.

    Designed for fast access with automatic eviction when full.

    Characteristics:
    - Fixed size (last 20-50 operations)
    - FIFO eviction policy
    - Thread-safe deque implementation
    - No persistence (lost on crash)

    Token Budget: ~5-10K tokens
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize working memory.

        Args:
            config: Configuration with 'orchestrator.working_memory' section
        """
        self.max_operations = config.get('orchestrator.working_memory.max_operations', 50)
        self.max_tokens = config.get('orchestrator.working_memory.max_tokens', 10000)

        # Storage (thread-safe deque)
        from collections import deque
        self._operations = deque(maxlen=self.max_operations)
        self._current_tokens = 0
        self._lock = RLock()

    def add_operation(self, operation: Dict[str, Any]) -> None:
        """Add operation to working memory.

        Auto-evicts oldest if at capacity.
        """
        with self._lock:
            # Evict if token limit exceeded
            while self._current_tokens > self.max_tokens and self._operations:
                evicted = self._operations.popleft()
                self._current_tokens -= evicted.get('tokens', 0)

            # Add new operation
            self._operations.append(operation)
            self._current_tokens += operation.get('tokens', 0)

    def get_recent_operations(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get recent operations (most recent first)."""
        with self._lock:
            ops = list(self._operations)
            ops.reverse()  # Most recent first
            return ops[:limit] if limit else ops

    def get_operations(
        self,
        operation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get operations, optionally filtered by type."""
        with self._lock:
            ops = list(self._operations)
            ops.reverse()

            if operation_type:
                ops = [op for op in ops if op.get('type') == operation_type]

            return ops[:limit]

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Simple keyword search in working memory."""
        with self._lock:
            query_lower = query.lower()
            results = []

            for op in reversed(self._operations):  # Recent first
                op_str = str(op.get('data', ''))
                if query_lower in op_str.lower():
                    results.append(op_str)
                    if len(results) >= max_results:
                        break

            return results

    def clear(self) -> None:
        """Clear all working memory."""
        with self._lock:
            self._operations.clear()
            self._current_tokens = 0

    def get_all_operations(self) -> List[Dict[str, Any]]:
        """Get all operations (for flushing to session memory)."""
        with self._lock:
            return list(self._operations)

    def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics."""
        with self._lock:
            return {
                'operation_count': len(self._operations),
                'current_tokens': self._current_tokens,
                'max_tokens': self.max_tokens,
                'utilization': self._current_tokens / self.max_tokens if self.max_tokens > 0 else 0
            }
```

---

### 3.3 SessionMemoryManager (Tier 2 - Documents)

**Purpose**: Maintain chronological session narrative with compression

**Location**: `src/orchestration/memory/session_memory_manager.py`

**Document Format** (`.obra/sessions/session_<uuid>.md`):
```markdown
# Orchestrator Session: 2025-01-15 14:30:00

**Session ID**: 550e8400-e29b-41d4-a716-446655440000
**Project**: obra (ID: 1)
**Started**: 2025-01-15 14:30:00 UTC
**Status**: Active

---

## Operations Log

### [14:30:15] NL Command: Create Epic
**Intent**: CREATE operation for EPIC entity
**Input**: "Create an epic for user authentication system"
**Result**: Created Epic #5 "User Authentication System"
**Tokens**: 1,234

### [14:31:42] NL Command: Create Stories
**Intent**: CREATE operation for STORY entities
**Input**: "Add 3 stories to it: login, signup, and MFA"
**Result**: Created Stories #10, #11, #12 under Epic #5
**Tokens**: 1,567

### [14:35:20] Task Execution
**Task**: #15 "Implement password hashing module"
**Iterations**: 3
**Quality Score**: 0.87
**Decision**: PROCEED
**Tokens**: 8,945

---

## Session Summary

**Total Operations**: 12
**Commands**: 5 NL commands, 3 task executions, 4 validations
**Tokens Used**: 24,567 / 128,000 (19.2%)
**Issues**: None
**Blockers**: None

---

## Current State

**Active Work**:
- Epic #5 (User Authentication) - 3 stories created, 1 in progress

**Recent Decisions**:
- Approved password hashing implementation (bcrypt + salt)
- Deferred OAuth integration to next sprint

**Next Steps**:
- Complete Task #15 (password hashing)
- Start Task #16 (token generation)
```

**Implementation**:
```python
class SessionMemoryManager:
    """Manage session-scoped memory documents.

    Features:
    - Append-only session log
    - Periodic compression (when >40K tokens)
    - Session summary generation
    - Archival on session end

    Token Budget: 20-50K tokens (auto-compress at 40K)
    """

    def __init__(self, config: Dict[str, Any], llm_interface: LocalLLMInterface):
        """Initialize session memory manager."""
        self.config = config
        self.llm = llm_interface
        self.session_dir = Path(config.get('orchestrator.session_dir', '.obra/sessions'))
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Current session
        self.session_id = str(uuid.uuid4())
        self.session_file = self.session_dir / f"session_{self.session_id}.md"
        self.started_at = datetime.now(UTC)

        # Tracking
        self._operation_count = 0
        self._current_tokens = 0
        self._lock = RLock()

        # Initialize session document
        self._initialize_session_doc()

    def _initialize_session_doc(self) -> None:
        """Create initial session document."""
        header = f"""# Orchestrator Session: {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}

**Session ID**: {self.session_id}
**Project**: {self.config.get('project.name', 'Unknown')} (ID: {self.config.get('project.id', 'N/A')})
**Started**: {self.started_at.isoformat()}
**Status**: Active

---

## Operations Log

"""
        self.session_file.write_text(header)
        self._current_tokens = self._estimate_tokens(header)

    def append_operations(self, operations: List[Dict[str, Any]]) -> None:
        """Append operations to session document."""
        with self._lock:
            entries = []

            for op in operations:
                timestamp = op.get('timestamp', datetime.now(UTC))
                op_type = op.get('type', 'unknown')
                data = op.get('data', {})
                tokens = op.get('tokens', 0)

                entry = self._format_operation_entry(timestamp, op_type, data, tokens)
                entries.append(entry)
                self._current_tokens += self._estimate_tokens(entry)
                self._operation_count += 1

            # Append to file
            with open(self.session_file, 'a') as f:
                f.write('\n'.join(entries) + '\n')

            # Compress if needed
            if self._current_tokens > 40000:
                self.compress()

    def _format_operation_entry(
        self,
        timestamp: datetime,
        op_type: str,
        data: Dict[str, Any],
        tokens: int
    ) -> str:
        """Format single operation entry."""
        time_str = timestamp.strftime('%H:%M:%S')

        if op_type == 'nl_command':
            return f"""### [{time_str}] NL Command: {data.get('intent_type', 'Unknown')}
**Input**: "{data.get('user_input', '')}"
**Result**: {data.get('result', 'N/A')}
**Tokens**: {tokens:,}
"""
        elif op_type == 'task_execution':
            return f"""### [{time_str}] Task Execution
**Task**: #{data.get('task_id')} "{data.get('task_title', '')}"
**Iterations**: {data.get('iterations', 0)}
**Quality Score**: {data.get('quality_score', 0.0):.2f}
**Decision**: {data.get('decision', 'N/A')}
**Tokens**: {tokens:,}
"""
        else:
            return f"""### [{time_str}] {op_type.replace('_', ' ').title()}
**Data**: {str(data)[:200]}...
**Tokens**: {tokens:,}
"""

    def compress(self) -> None:
        """Compress session document using summarization.

        Strategy:
        1. Keep last hour detailed
        2. Summarize older content
        3. Preserve critical decisions/issues

        Target: 30% compression ratio
        """
        with self._lock:
            logger.info(f"Compressing session {self.session_id} ({self._current_tokens} tokens)")

            # Read current document
            current_content = self.session_file.read_text()

            # Split into header, recent (last hour), and older
            header, operations_section = self._split_document(current_content)

            # Identify cutoff (last hour = detailed, older = summarize)
            cutoff_time = datetime.now(UTC) - timedelta(hours=1)
            recent_ops, older_ops = self._split_by_time(operations_section, cutoff_time)

            # Summarize older operations
            if older_ops:
                summary = self.llm.send_prompt(f"""Summarize the following Orchestrator session operations concisely, preserving:
1. Critical decisions made
2. Issues/blockers encountered
3. Key tasks completed
4. Overall progress

Target: ~{len(older_ops) // 3} words

Operations:
{older_ops}

Summary:""")

                compressed_older = f"""## Earlier Operations (Summarized)

{summary}

---

"""
            else:
                compressed_older = ""

            # Reconstruct document
            new_content = header + compressed_older + "## Recent Operations\n\n" + recent_ops

            # Write compressed version
            self.session_file.write_text(new_content)

            # Update token count
            old_tokens = self._current_tokens
            self._current_tokens = self._estimate_tokens(new_content)
            compression_ratio = self._current_tokens / old_tokens if old_tokens > 0 else 1.0

            logger.info(f"Compression complete: {old_tokens} → {self._current_tokens} tokens ({compression_ratio:.2%})")

    def generate_summary(self) -> Dict[str, Any]:
        """Generate structured summary of session.

        Returns:
            Dictionary with session insights for episodic memory integration
        """
        content = self.session_file.read_text()

        summary_prompt = f"""Analyze this Orchestrator session and provide a structured summary:

{content}

Provide summary in JSON format:
{{
    "total_operations": <count>,
    "key_accomplishments": [<list of key things done>],
    "decisions_made": [<list of important decisions>],
    "issues_encountered": [<list of problems/blockers>],
    "project_state_changes": "<brief description of how project state changed>",
    "recommended_next_steps": [<list of logical next actions>]
}}
"""

        summary_json = self.llm.send_prompt(summary_prompt)
        # Parse JSON (with error handling)
        try:
            summary = json.loads(summary_json)
        except json.JSONDecodeError:
            logger.warning("Failed to parse session summary JSON, using fallback")
            summary = {
                'total_operations': self._operation_count,
                'key_accomplishments': [],
                'decisions_made': [],
                'issues_encountered': [],
                'project_state_changes': 'Unable to generate summary',
                'recommended_next_steps': []
            }

        return summary

    def archive(self) -> Path:
        """Archive session document.

        Moves session file to archive directory with timestamp.

        Returns:
            Path to archived file
        """
        archive_dir = self.session_dir / 'archive'
        archive_dir.mkdir(exist_ok=True)

        archive_name = f"session_{self.started_at.strftime('%Y%m%d_%H%M%S')}_{self.session_id[:8]}.md"
        archive_path = archive_dir / archive_name

        # Move file
        self.session_file.rename(archive_path)

        logger.info(f"Session archived to {archive_path}")
        return archive_path

    def get_summary(self, max_tokens: int) -> str:
        """Get summary of current session (for context building)."""
        content = self.session_file.read_text()

        # If under budget, return full content
        if self._current_tokens <= max_tokens:
            return content

        # Otherwise, summarize
        summary = self.llm.send_prompt(f"""Summarize this Orchestrator session in {max_tokens} tokens or less:

{content}

Summary:""")

        return summary

    def get_current_state(self) -> Dict[str, Any]:
        """Get current session state (for episodic memory updates)."""
        return {
            'session_id': self.session_id,
            'operation_count': self._operation_count,
            'tokens_used': self._current_tokens,
            'started_at': self.started_at,
            'duration_seconds': (datetime.now(UTC) - self.started_at).total_seconds()
        }

    def token_count(self) -> int:
        """Get current token count."""
        return self._current_tokens

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Search session document."""
        content = self.session_file.read_text()
        lines = content.split('\n')

        query_lower = query.lower()
        results = []

        for line in lines:
            if query_lower in line.lower():
                results.append(line)
                if len(results) >= max_results:
                    break

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get session memory statistics."""
        return {
            'session_id': self.session_id,
            'operation_count': self._operation_count,
            'current_tokens': self._current_tokens,
            'session_age_seconds': (datetime.now(UTC) - self.started_at).total_seconds()
        }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens in text (4 chars per token heuristic)."""
        return len(text) // 4

    def _split_document(self, content: str) -> Tuple[str, str]:
        """Split document into header and operations."""
        parts = content.split('## Operations Log', 1)
        if len(parts) == 2:
            return parts[0] + '## Operations Log\n\n', parts[1]
        return content, ""

    def _split_by_time(
        self,
        operations: str,
        cutoff: datetime
    ) -> Tuple[str, str]:
        """Split operations into recent and older based on time cutoff."""
        # This is simplified - real implementation would parse timestamps
        # For now, keep last 30% as recent
        lines = operations.split('\n')
        cutoff_line = int(len(lines) * 0.7)

        older = '\n'.join(lines[:cutoff_line])
        recent = '\n'.join(lines[cutoff_line:])

        return recent, older
```

---

### 3.4 EpisodicMemoryManager (Tier 3 - Long-term Documents)

**Purpose**: Maintain canonical project state and history

**Location**: `src/orchestration/memory/episodic_memory_manager.py`

**Document Types**:

1. **`project_state.md`** - Current project snapshot
2. **`work_plan.md`** - What's next (prioritized backlog)
3. **`decision_log.md`** - Important decisions made

**Implementation**:
```python
class EpisodicMemoryManager:
    """Manage long-term project memory documents.

    Maintains canonical documents that summarize project state:
    - Project state: Current snapshot of active work
    - Work plan: Prioritized next steps
    - Decision log: Compressed history of decisions

    Documents are periodically refreshed to prevent bloat.

    Token Budget: 10-30K tokens per document
    """

    def __init__(self, config: Dict[str, Any], llm_interface: LocalLLMInterface):
        """Initialize episodic memory manager."""
        self.config = config
        self.llm = llm_interface
        self.memory_dir = Path(config.get('orchestrator.memory_dir', '.obra/memory'))
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Document paths
        self.project_state_file = self.memory_dir / 'project_state.md'
        self.work_plan_file = self.memory_dir / 'work_plan.md'
        self.decision_log_file = self.memory_dir / 'decision_log.md'

        # Versioning for history preservation
        self.versions_dir = self.memory_dir / 'versions'
        self.versions_dir.mkdir(exist_ok=True)

        # Initialize if not exist
        self._ensure_documents_exist()

        self._lock = RLock()

    def _ensure_documents_exist(self) -> None:
        """Create initial documents if they don't exist."""
        if not self.project_state_file.exists():
            self.project_state_file.write_text("""# Project State

**Last Updated**: Never
**Status**: Uninitialized

No project state recorded yet.
""")

        if not self.work_plan_file.exists():
            self.work_plan_file.write_text("""# Work Plan

**Last Updated**: Never

No work plan recorded yet.
""")

        if not self.decision_log_file.exists():
            self.decision_log_file.write_text("""# Decision Log

**Last Updated**: Never

No decisions recorded yet.
""")

    def integrate_session(self, session_summary: Dict[str, Any]) -> None:
        """Integrate session insights into episodic memory.

        Called when session ends. Updates all episodic documents.

        Args:
            session_summary: Structured summary from SessionMemoryManager.generate_summary()
        """
        with self._lock:
            # Update project state
            self.update_project_state(session_summary)

            # Update work plan
            self._update_work_plan(session_summary.get('recommended_next_steps', []))

            # Add decisions to decision log
            for decision in session_summary.get('decisions_made', []):
                self._append_decision(decision)

            # Compress documents if too large
            self._compress_if_needed()

    def update_project_state(self, session_data: Dict[str, Any]) -> None:
        """Update project_state.md with latest information.

        Strategy: Replace with fresh state, version old one
        """
        with self._lock:
            # Version current state
            self._version_document(self.project_state_file)

            # Query StateManager for current facts
            # (This would integrate with StateManager - simplified here)
            current_state = self._query_current_state()

            # Generate new state document
            new_state = f"""# Project State

**Last Updated**: {datetime.now(UTC).isoformat()}
**Session**: {session_data.get('session_id', 'N/A')}

## Active Work

{current_state['active_work']}

## Recent Progress

{session_data.get('project_state_changes', 'No changes')}

## Blockers

{current_state['blockers']}

## Statistics

- **Total Epics**: {current_state['epic_count']}
- **Total Stories**: {current_state['story_count']}
- **Total Tasks**: {current_state['task_count']}
- **Completed**: {current_state['completed_count']}
- **In Progress**: {current_state['in_progress_count']}
- **Blocked**: {current_state['blocked_count']}
"""

            self.project_state_file.write_text(new_state)

    def _update_work_plan(self, next_steps: List[str]) -> None:
        """Update work_plan.md with recommended next steps."""
        with self._lock:
            # Version current plan
            self._version_document(self.work_plan_file)

            # Query StateManager for prioritized backlog
            backlog = self._query_backlog()

            # Generate new work plan
            new_plan = f"""# Work Plan

**Last Updated**: {datetime.now(UTC).isoformat()}

## Immediate Next Steps

{self._format_list(next_steps)}

## Prioritized Backlog

{backlog}

## Future Work

- (To be determined based on milestone completion)
"""

            self.work_plan_file.write_text(new_plan)

    def _append_decision(self, decision: str) -> None:
        """Append decision to decision_log.md.

        Uses append-only log with periodic compression.
        """
        with self._lock:
            timestamp = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
            entry = f"\n### [{timestamp}] {decision}\n"

            with open(self.decision_log_file, 'a') as f:
                f.write(entry)

    def _compress_if_needed(self) -> None:
        """Compress documents if they exceed token limits."""
        for doc_file in [self.project_state_file, self.work_plan_file, self.decision_log_file]:
            token_count = self._estimate_tokens(doc_file.read_text())

            if token_count > 30000:
                logger.info(f"Compressing {doc_file.name} ({token_count} tokens)")
                self._compress_document(doc_file)

    def _compress_document(self, doc_path: Path) -> None:
        """Compress document using LLM summarization.

        Strategy:
        1. Version current document
        2. Summarize to target size (30% reduction)
        3. Preserve critical information
        """
        # Version before compression
        self._version_document(doc_path)

        # Read current content
        content = doc_path.read_text()
        current_tokens = self._estimate_tokens(content)
        target_tokens = int(current_tokens * 0.7)  # 30% reduction

        # Summarize
        summary = self.llm.send_prompt(f"""Compress this document to approximately {target_tokens} tokens while preserving all critical information:

{content}

Compressed version:""")

        # Write compressed version
        doc_path.write_text(summary)

        new_tokens = self._estimate_tokens(summary)
        logger.info(f"Compressed {doc_path.name}: {current_tokens} → {new_tokens} tokens")

    def _version_document(self, doc_path: Path) -> Path:
        """Create versioned backup of document.

        Returns:
            Path to versioned file
        """
        timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
        version_name = f"{doc_path.stem}_{timestamp}.md"
        version_path = self.versions_dir / version_name

        # Copy current to version
        if doc_path.exists():
            version_path.write_text(doc_path.read_text())

        return version_path

    def get_project_state(self, max_tokens: int) -> str:
        """Get project state document (for context building)."""
        content = self.project_state_file.read_text()

        if self._estimate_tokens(content) <= max_tokens:
            return content

        # Summarize if over budget
        return self.llm.send_prompt(f"""Summarize to {max_tokens} tokens:\n\n{content}\n\nSummary:""")

    def get_work_plan(self, max_tokens: int) -> str:
        """Get work plan document."""
        content = self.work_plan_file.read_text()

        if self._estimate_tokens(content) <= max_tokens:
            return content

        return self.llm.send_prompt(f"""Summarize to {max_tokens} tokens:\n\n{content}\n\nSummary:""")

    def get_recent_decisions(self, max_tokens: int) -> List[str]:
        """Get recent decisions from decision log."""
        content = self.decision_log_file.read_text()

        # Extract last N decisions that fit in budget
        lines = content.split('\n')
        decisions = []
        current_tokens = 0

        for line in reversed(lines):
            if line.startswith('###'):
                line_tokens = self._estimate_tokens(line)
                if current_tokens + line_tokens > max_tokens:
                    break
                decisions.insert(0, line)
                current_tokens += line_tokens

        return decisions

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Search episodic memory documents."""
        results = []

        for doc_path in [self.project_state_file, self.work_plan_file, self.decision_log_file]:
            content = doc_path.read_text()
            lines = content.split('\n')

            for line in lines:
                if query.lower() in line.lower():
                    results.append(f"[{doc_path.name}] {line}")
                    if len(results) >= max_results:
                        return results

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics."""
        return {
            'project_state_tokens': self._estimate_tokens(self.project_state_file.read_text()),
            'work_plan_tokens': self._estimate_tokens(self.work_plan_file.read_text()),
            'decision_log_tokens': self._estimate_tokens(self.decision_log_file.read_text()),
            'version_count': len(list(self.versions_dir.glob('*.md')))
        }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens (4 chars per token)."""
        return len(text) // 4

    def _query_current_state(self) -> Dict[str, Any]:
        """Query StateManager for current project state.

        (Simplified - real implementation would integrate with StateManager)
        """
        return {
            'active_work': 'Epic #5 (User Authentication) - 3/5 stories complete',
            'blockers': 'None',
            'epic_count': 10,
            'story_count': 45,
            'task_count': 234,
            'completed_count': 189,
            'in_progress_count': 12,
            'blocked_count': 0
        }

    def _query_backlog(self) -> str:
        """Query StateManager for prioritized backlog."""
        return """1. Epic #6 (Payment Processing) - 5 stories, high priority
2. Epic #7 (Notification System) - 3 stories, medium priority
3. Epic #8 (Analytics Dashboard) - 8 stories, low priority"""

    def _format_list(self, items: List[str]) -> str:
        """Format list items as markdown."""
        if not items:
            return '- None'
        return '\n'.join(f'- {item}' for item in items)
```

---

### 3.5 ContextWindowTracker

**Purpose**: Monitor Orchestrator's token usage across operations

**Location**: `src/orchestration/memory/context_window_tracker.py`

**Implementation**:
```python
class ContextWindowTracker:
    """Track Orchestrator's context window usage.

    Monitors cumulative token usage across operations and triggers
    refresh when thresholds are reached.

    Similar to Claude Code session tracking but for Orchestrator's own context.
    """

    def __init__(
        self,
        max_tokens: int,
        warning_threshold: float = 0.70,
        refresh_threshold: float = 0.80,
        critical_threshold: float = 0.95
    ):
        """Initialize context window tracker.

        Args:
            max_tokens: Maximum context window size (e.g., 128000 for Qwen)
            warning_threshold: Warn at this percentage (default 70%)
            refresh_threshold: Auto-refresh at this percentage (default 80%)
            critical_threshold: Critical level (default 95%)
        """
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.refresh_threshold = refresh_threshold
        self.critical_threshold = critical_threshold

        # Tracking
        self._used_tokens = 0
        self._operation_count = 0
        self.refresh_count = 0
        self._lock = RLock()

        logger.info(f"ContextWindowTracker initialized: {max_tokens} tokens, refresh at {refresh_threshold:.0%}")

    def add_usage(self, tokens: int) -> None:
        """Record token usage from an operation.

        Args:
            tokens: Tokens consumed by operation
        """
        with self._lock:
            self._used_tokens += tokens
            self._operation_count += 1

            # Check thresholds
            usage_pct = self.usage_percentage()

            if usage_pct >= self.critical_threshold:
                logger.error(
                    f"CONTEXT_WINDOW CRITICAL: {usage_pct:.1%} "
                    f"({self._used_tokens:,}/{self.max_tokens:,} tokens)"
                )
            elif usage_pct >= self.refresh_threshold:
                logger.warning(
                    f"CONTEXT_WINDOW REFRESH: {usage_pct:.1%} "
                    f"({self._used_tokens:,}/{self.max_tokens:,} tokens) - auto-refresh needed"
                )
            elif usage_pct >= self.warning_threshold:
                logger.info(
                    f"CONTEXT_WINDOW WARNING: {usage_pct:.1%} "
                    f"({self._used_tokens:,}/{self.max_tokens:,} tokens) - approaching refresh"
                )

    def should_refresh(self) -> bool:
        """Check if context refresh is needed.

        Returns:
            True if usage >= refresh_threshold
        """
        return self.usage_percentage() >= self.refresh_threshold

    def reset(self) -> None:
        """Reset tracker after context refresh."""
        with self._lock:
            old_usage = self._used_tokens
            self._used_tokens = 0
            self._operation_count = 0
            self.refresh_count += 1

            logger.info(
                f"Context window reset: {old_usage:,} tokens freed, "
                f"refresh #{self.refresh_count}"
            )

    def used_tokens(self) -> int:
        """Get current token usage."""
        return self._used_tokens

    def available_tokens(self) -> int:
        """Get remaining tokens."""
        return max(0, self.max_tokens - self._used_tokens)

    def usage_percentage(self) -> float:
        """Get usage as percentage (0.0-1.0)."""
        return self._used_tokens / self.max_tokens if self.max_tokens > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        return {
            'used_tokens': self._used_tokens,
            'available_tokens': self.available_tokens(),
            'max_tokens': self.max_tokens,
            'usage_percentage': self.usage_percentage(),
            'operation_count': self._operation_count,
            'refresh_count': self.refresh_count
        }
```

---

### 3.6 MemoryCompressor

**Purpose**: Compress/summarize memory content using LLM

**Location**: `src/orchestration/memory/memory_compressor.py`

**Implementation**:
```python
class MemoryCompressor:
    """Compress memory content using LLM-based summarization.

    Strategies:
    - Hierarchical summarization (detailed → medium → brief)
    - Importance-based compression (keep critical facts)
    - Time-windowed compression (recent detailed, old summarized)
    """

    def __init__(
        self,
        context_builder: ContextManager,
        llm_interface: LocalLLMInterface
    ):
        """Initialize memory compressor."""
        self.context_builder = context_builder
        self.llm = llm_interface

    def compress_operations(
        self,
        operations: List[Dict[str, Any]],
        target_tokens: int,
        preserve_critical: bool = True
    ) -> str:
        """Compress list of operations to target size.

        Args:
            operations: List of operation dictionaries
            target_tokens: Target token count
            preserve_critical: If True, keep critical operations intact

        Returns:
            Compressed narrative string
        """
        # Convert operations to text
        ops_text = '\n'.join(
            f"[{op['timestamp']}] {op['type']}: {op['data']}"
            for op in operations
        )

        # Identify critical operations (if requested)
        critical_ops = []
        routine_ops = operations

        if preserve_critical:
            critical_ops = [
                op for op in operations
                if self._is_critical(op)
            ]
            routine_ops = [
                op for op in operations
                if not self._is_critical(op)
            ]

        # Summarize routine operations
        if routine_ops:
            routine_text = '\n'.join(
                f"[{op['timestamp']}] {op['type']}: {op['data']}"
                for op in routine_ops
            )

            summary = self.llm.send_prompt(f"""Summarize these operations concisely:

{routine_text}

Target: ~{target_tokens // 2} tokens
Focus on: Key accomplishments, decisions made, issues encountered

Summary:""")
        else:
            summary = ""

        # Preserve critical operations verbatim
        if critical_ops:
            critical_text = '\n'.join(
                f"[{op['timestamp']}] {op['type']}: {op['data']}"
                for op in critical_ops
            )

            return f"{summary}\n\n**Critical Operations**:\n{critical_text}"

        return summary

    def hierarchical_summarize(
        self,
        text: str,
        levels: int = 3
    ) -> List[str]:
        """Create hierarchical summaries (detailed → brief).

        Args:
            text: Text to summarize
            levels: Number of summary levels (default 3)

        Returns:
            List of summaries, from most detailed to briefest
        """
        summaries = [text]
        current_text = text
        current_tokens = self._estimate_tokens(text)

        for level in range(1, levels):
            target_tokens = current_tokens // 2  # Halve each level

            summary = self.llm.send_prompt(f"""Summarize to {target_tokens} tokens:

{current_text}

Summary:""")

            summaries.append(summary)
            current_text = summary
            current_tokens = self._estimate_tokens(summary)

        return summaries

    def _is_critical(self, operation: Dict[str, Any]) -> bool:
        """Determine if operation is critical.

        Critical operations:
        - Decisions made
        - Errors/failures
        - Milestone completions
        - Epic/story completions
        """
        op_type = operation.get('type', '')
        data = operation.get('data', {})

        # Decision operations are critical
        if op_type == 'decision':
            return True

        # Failed operations are critical
        if data.get('status') == 'failed':
            return True

        # Milestone/epic completions are critical
        if 'milestone' in str(data).lower() or 'epic' in str(data).lower():
            if data.get('status') == 'completed':
                return True

        return False

    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens in text."""
        return len(text) // 4
```

---

## 4. Integration with Existing System

### 4.1 Orchestrator Changes

**Location**: `src/orchestrator.py`

**Integration Points**:

```python
class Orchestrator:
    """Main orchestration loop with context management."""

    def __init__(self, config: Config):
        # ... existing initialization ...

        # NEW: Initialize Orchestrator Context Manager
        self.orch_context = OrchestratorContextManager(
            state_manager=self.state_manager,
            context_builder=self.context_manager,  # Existing ContextManager
            llm_interface=self.llm_interface,       # Existing LLM
            config=config.data
        )

        logger.info("Orchestrator context management initialized")

    def execute_task(self, task_id: int, **kwargs) -> Dict[str, Any]:
        """Execute task with context tracking."""

        # Get Orchestrator's context for this operation
        orch_context = self.orch_context.get_orchestrator_context(
            for_operation='task_execution'
        )

        # ... existing task execution logic ...

        # Track this operation
        self.orch_context.record_operation(
            operation_type='task_execution',
            operation_data={
                'task_id': task_id,
                'task_title': task.title,
                'result': result,
                'quality_score': quality_score,
                'decision': decision
            },
            tokens_used=total_tokens_used
        )

        return result

    def execute_nl_command(
        self,
        parsed_intent: 'ParsedIntent',
        project_id: int,
        interactive: bool = False
    ) -> Dict[str, Any]:
        """Execute NL command with context tracking."""

        # Get Orchestrator's context
        orch_context = self.orch_context.get_orchestrator_context(
            for_operation='nl_command'
        )

        # Check if Orch remembers previous context (for "it", "that", etc.)
        if self._requires_reference_resolution(parsed_intent):
            recent_ops = self.orch_context.query_recent_operations(limit=5)
            # Use recent_ops to resolve "it", "that" references

        # ... existing NL command execution ...

        # Track operation
        self.orch_context.record_operation(
            operation_type='nl_command',
            operation_data={
                'intent': parsed_intent.intent_type,
                'operation': parsed_intent.operation_type,
                'user_input': parsed_intent.original_message,
                'result': result
            },
            tokens_used=tokens_used
        )

        return result

    def shutdown(self, graceful: bool = True) -> None:
        """Shutdown with session flush."""
        if graceful:
            # Flush Orchestrator's session
            archive_path = self.orch_context.flush_session()
            logger.info(f"Orchestrator session archived to {archive_path}")

        # ... existing shutdown logic ...
```

### 4.2 NLCommandProcessor Integration

**Location**: `src/nl/nl_command_processor.py`

```python
class NLCommandProcessor:
    """NL command processor with context awareness."""

    def __init__(self, ..., orch_context: OrchestratorContextManager):
        # ... existing init ...
        self.orch_context = orch_context  # NEW

    def process(self, user_input: str, ...) -> ParsedIntent:
        """Process NL command with context from Orchestrator."""

        # Get recent context for reference resolution
        if self._has_pronouns(user_input):  # "it", "that", "this", etc.
            recent_context = self.orch_context.query_recent_operations(
                operation_type='nl_command',
                limit=5
            )
            # Use recent_context to resolve references

        # ... existing processing logic ...
```

### 4.3 Configuration Schema

**Location**: `config/default_config.yaml`

**New Section**:
```yaml
orchestrator:
  # Context window configuration (for Orchestrator LLM, NOT Implementer)
  context_window:
    max_tokens: 128000  # Qwen 2.5 Coder context window
    warning_threshold: 0.70   # 70% usage warning
    refresh_threshold: 0.80   # 80% triggers auto-refresh
    critical_threshold: 0.95  # 95% critical warning

  # Working memory (Tier 1)
  working_memory:
    max_operations: 50      # Keep last 50 operations
    max_tokens: 10000       # ~10K token budget

  # Session memory (Tier 2)
  session_dir: '.obra/sessions'
  session_compression_threshold: 40000  # Compress at 40K tokens
  session_compression_ratio: 0.7        # Target 30% reduction

  # Episodic memory (Tier 3)
  memory_dir: '.obra/memory'
  episodic_compression_threshold: 30000  # Compress at 30K tokens per doc
  keep_versions: 10  # Keep last 10 versions of each document

  # Refresh behavior
  auto_refresh_enabled: true
  refresh_latency_target_ms: 5000  # Target <5s refresh
```

---

## 5. Usage Examples

### 5.1 Normal Operation Flow

```python
# User starts interactive session
orchestrator = Orchestrator(config)
orchestrator.initialize()

# User: "Create epic for user authentication"
orchestrator.execute_nl_command(parsed_intent, project_id=1)
# → Recorded in working memory (512 tokens)

# User: "Add 3 stories to it"
orchestrator.execute_nl_command(parsed_intent, project_id=1)
# → Orch queries recent operations, resolves "it" to Epic #5
# → Recorded in working memory (387 tokens)

# ... 15 more commands ...

# Context usage: 18,234 / 128,000 tokens (14.2%)
# No refresh needed yet

# ... 30 more operations ...

# Context usage: 102,456 / 128,000 tokens (80.0%)
# AUTO-REFRESH TRIGGERED:
# 1. Flush working memory → session document
# 2. Compress session document (102K → 71K tokens)
# 3. Update episodic memory (project_state.md)
# 4. Reset context tracker
# Context usage: 5,234 / 128,000 tokens (4.1%)

# Session continues seamlessly
```

### 5.2 Context Query Example

```python
# User asks: "What did we just do?"
recent_ops = orchestrator.orch_context.query_recent_operations(limit=10)

# Returns:
[
    {'type': 'nl_command', 'data': {'intent': 'CREATE', 'result': 'Created Story #12'}, ...},
    {'type': 'nl_command', 'data': {'intent': 'CREATE', 'result': 'Created Story #11'}, ...},
    {'type': 'task_execution', 'data': {'task_id': 15, 'result': 'completed'}, ...},
    # ... 7 more operations
]

# Orchestrator can answer: "We just created 2 stories (#11, #12) and executed task #15."
```

### 5.3 Session End Flow

```python
# User ends session (Ctrl+C, /stop, timeout, etc.)
orchestrator.shutdown(graceful=True)

# Shutdown process:
# 1. Generate session summary (LLM call)
# 2. Archive session document to .obra/sessions/archive/
# 3. Integrate session insights into episodic memory:
#    - Update project_state.md
#    - Update work_plan.md
#    - Append to decision_log.md
# 4. Compress episodic documents if needed
# 5. Exit

# Next session:
# - Working memory: empty (fresh start)
# - Session memory: new session document
# - Episodic memory: preserved (project_state, work_plan, decisions)
# → Continuity maintained across sessions!
```

---

## 6. Performance Analysis

### 6.1 Latency Targets

| Operation | Target (P95) | Estimated |
|-----------|--------------|-----------|
| Record operation | <10ms | ~5ms (in-memory append) |
| Get context | <100ms | ~50ms (file reads) |
| Context refresh | <5s | ~3s (compression + I/O) |
| Session flush | <10s | ~7s (summary generation) |

### 6.2 Memory Overhead

| Component | Memory Usage |
|-----------|--------------|
| WorkingMemory | ~2MB (50 operations) |
| SessionMemoryManager | ~5MB (40K tokens) |
| EpisodicMemoryManager | ~10MB (3 documents) |
| **Total** | **~17MB** |

**Target**: <100MB (NFR2) → **✅ Well under limit**

### 6.3 Compression Ratios

| Strategy | Expected Ratio | Validated |
|----------|----------------|-----------|
| Session compression | 0.7 (30% reduction) | TBD |
| Episodic compression | 0.7 (30% reduction) | TBD |
| Hierarchical (3 levels) | 0.125 (87.5% reduction) | TBD |

**Target**: ≥0.7 (NFR3) → **Expected to meet**

### 6.4 Scalability

**Scenario**: Large project (50 epics, 200 stories, 1000 tasks)

| Tier | Growth Rate | Size at 1000 tasks |
|------|-------------|-------------------|
| Working Memory | O(1) - fixed size | 10K tokens (50 ops) |
| Session Memory | O(n) - linear with session ops | 40K tokens (100 ops/session) |
| Episodic Memory | O(log n) - sub-linear with compression | 30K tokens (compressed) |
| **Total Context** | **O(log n)** | **~80K tokens** |

**Context Window**: 128K tokens
**Utilization**: 62.5% → **✅ Under 80% refresh threshold**

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Target Coverage**: ≥90% for new components

**Test Files**:
- `tests/orchestration/test_orchestrator_context_manager.py`
- `tests/orchestration/test_working_memory.py`
- `tests/orchestration/test_session_memory_manager.py`
- `tests/orchestration/test_episodic_memory_manager.py`
- `tests/orchestration/test_context_window_tracker.py`
- `tests/orchestration/test_memory_compressor.py`

**Key Test Scenarios**:
```python
def test_working_memory_eviction():
    """Test FIFO eviction when max operations reached."""

def test_session_compression():
    """Test compression achieves ≥0.7 ratio."""

def test_context_refresh_trigger():
    """Test auto-refresh at 80% threshold."""

def test_session_flush():
    """Test session summary generation and archival."""

def test_episodic_integration():
    """Test session insights integrated into episodic docs."""

def test_reference_resolution():
    """Test resolving 'it', 'that' from recent operations."""

def test_concurrent_access():
    """Test thread safety with concurrent operations."""
```

### 7.2 Integration Tests

**Test Scenarios**:
```python
def test_long_session_continuity():
    """Test 100+ operations without context overflow."""

def test_cross_session_continuity():
    """Test project state preserved across sessions."""

def test_context_query():
    """Test 'what did we just do?' queries."""

def test_reference_resolution_integration():
    """Test 'add 3 stories to it' after 'create epic'."""

def test_graceful_degradation():
    """Test behavior when context limit hit."""
```

### 7.3 Performance Tests

```python
def test_refresh_latency():
    """Verify context refresh completes in <5s (P95)."""

def test_memory_overhead():
    """Verify memory usage <100MB."""

def test_compression_ratio():
    """Verify compression achieves ≥0.7 ratio."""

def test_scalability():
    """Test with 1000+ tasks."""
```

---

## 8. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)

**Stories**:
1. Implement WorkingMemory class
2. Implement ContextWindowTracker class
3. Implement MemoryCompressor class
4. Unit tests for core components (≥90% coverage)

**Deliverables**:
- 3 new modules (~600 lines)
- 50+ unit tests
- Documentation

### Phase 2: Session & Episodic Memory (Week 3-4)

**Stories**:
5. Implement SessionMemoryManager class
6. Implement EpisodicMemoryManager class
7. Document format design and versioning
8. Unit tests (≥90% coverage)

**Deliverables**:
- 2 new modules (~800 lines)
- 40+ unit tests
- Sample memory documents

### Phase 3: Integration (Week 5-6)

**Stories**:
9. Implement OrchestratorContextManager class
10. Integrate with Orchestrator.execute_task()
11. Integrate with Orchestrator.execute_nl_command()
12. Integrate with NLCommandProcessor (reference resolution)
13. Configuration schema updates
14. Integration tests

**Deliverables**:
- 1 new module (~500 lines)
- Orchestrator modifications (~200 lines)
- 30+ integration tests
- Config updates

### Phase 4: Polish & Validation (Week 7-8)

**Stories**:
15. Performance testing and optimization
16. Compression ratio validation
17. Reference resolution testing (pronouns)
18. Documentation (user guide, ADR)
19. Migration guide for existing projects

**Deliverables**:
- Performance test suite
- User documentation
- ADR-018: Orchestrator Context Management
- Migration guide

**Total Timeline**: 8 weeks
**Total Code**: ~2,100 lines (production) + ~1,200 lines (tests)

---

## 9. Risks & Mitigations

### Risk 1: LLM Summarization Quality

**Risk**: LLM summaries may lose critical information

**Mitigation**:
- Preserve critical operations verbatim (decisions, errors)
- Use hierarchical summarization (multiple detail levels)
- Version documents before compression (rollback if needed)
- Add manual override to disable auto-compression

### Risk 2: Refresh Latency

**Risk**: Context refresh may exceed 5s target

**Mitigation**:
- Profile compression operations
- Use async compression (don't block operations)
- Cache summarization prompts
- Implement fast-path compression (extractive vs generative)

### Risk 3: Memory Bloat

**Risk**: Memory documents may grow unbounded over time

**Mitigation**:
- Automatic archival of old session documents
- Periodic episodic document refresh (not append-only)
- Configurable retention policy (keep last N versions)
- Monitoring and alerts for document size

### Risk 4: Context Window Estimation Errors

**Risk**: Token estimation may be inaccurate (±10%)

**Mitigation**:
- Use conservative thresholds (80% vs 90%)
- Implement proper tokenization (not just char count)
- Track estimation accuracy and calibrate
- Fail-safe: If estimation wrong, hard limit at 95%

### Risk 5: Thread Safety

**Risk**: Concurrent access may cause race conditions

**Mitigation**:
- Use RLock for all components
- Atomic file operations (write to temp, rename)
- Test concurrent access scenarios
- Document thread safety guarantees

---

## 10. Future Enhancements

### v2.0: Semantic Search

**Feature**: Replace keyword search with semantic embeddings

**Benefits**:
- Better context retrieval
- "Find similar operations" queries
- Automatic clustering of related work

**Implementation**:
- Use sentence-transformers for embeddings
- Vector database (FAISS, Chroma)
- ~2 weeks additional work

### v2.1: Multi-Project Context

**Feature**: Maintain context across multiple projects

**Benefits**:
- Cross-project insights
- Pattern recognition across projects
- Shared decision library

**Implementation**:
- Project-scoped memory directories
- Shared global decision log
- ~1 week additional work

### v2.2: Context Visualization

**Feature**: Web UI for exploring Orchestrator memory

**Benefits**:
- Visualize context usage over time
- Browse session history
- Search across all memory tiers

**Implementation**:
- FastAPI backend
- React frontend
- ~3 weeks additional work

### v2.3: Adaptive Compression

**Feature**: Learn optimal compression strategies over time

**Benefits**:
- Better compression ratios
- Preserve what matters most
- Reduce false compressions

**Implementation**:
- Track compression effectiveness
- A/B test compression strategies
- ML-based importance prediction
- ~2 weeks additional work

---

## 11. Success Criteria

### Functional Success Criteria

- ✅ **FR1**: Track Orchestrator's context window usage in real-time
- ✅ **FR2**: Maintain persistent memory across operations within a session
- ✅ **FR3**: Preserve critical context across sessions (days/weeks)
- ✅ **FR4**: Automatically refresh context when approaching limits
- ✅ **FR5**: Provide "big picture" project awareness without loading all data
- ✅ **FR6**: Support natural language queries about recent operations

### Non-Functional Success Criteria

- ✅ **NFR1**: Context refresh latency <5s (P95)
- ✅ **NFR2**: Memory overhead <100MB for typical project
- ✅ **NFR3**: Document compression ratio ≥0.7 (30% size reduction)
- ✅ **NFR4**: Support projects with 1000+ tasks
- ✅ **NFR5**: Graceful degradation when context limits hit
- ✅ **NFR6**: Thread-safe for concurrent operations

### Acceptance Tests

**Test 1: Long Session Continuity**
```
Given: 100+ NL commands in single session
When: Context usage approaches 80%
Then: Auto-refresh occurs without data loss
And: Session continues seamlessly
```

**Test 2: Cross-Session Continuity**
```
Given: Session 1 creates Epic #5 with 3 stories
When: Session 2 starts next day
Then: Orchestrator knows Epic #5 exists in project state
And: Can answer "what's the status of Epic 5?"
```

**Test 3: Reference Resolution**
```
Given: User says "Create epic for authentication"
And: Orchestrator creates Epic #5
When: User says "Add 3 stories to it"
Then: Orchestrator resolves "it" to Epic #5
And: Creates stories under Epic #5
```

**Test 4: Context Compression**
```
Given: Session document reaches 40K tokens
When: Auto-compression triggered
Then: Document compressed to ≤28K tokens (≥0.7 ratio)
And: Critical operations preserved verbatim
```

---

## 12. Conclusion

This design proposes a comprehensive, multi-tier memory architecture for the Orchestrator that:

✅ **Solves the problem**: Orchestrator gains context continuity and awareness
✅ **Prevents bloat**: Automatic compression and intelligent refresh strategies
✅ **Scales gracefully**: Sub-linear growth with project size
✅ **Maintains performance**: <5s refresh latency, <100MB memory
✅ **Preserves history**: Versioned documents enable rollback
✅ **Enables intelligence**: "Big picture" awareness without loading all data

**Key Innovation**: Four-tier memory system (working → session → episodic → semantic) mirrors human cognition and provides the right balance of speed, persistence, and intelligence.

**Next Steps**:
1. Review this design with stakeholders
2. Gather feedback and refine approach
3. Create detailed implementation plan (task breakdown)
4. Begin Phase 1 development (core infrastructure)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-15
**Status**: Draft for Review
**Related ADRs**: TBD (will create ADR-018 after approval)
