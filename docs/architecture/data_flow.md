# Data Flow Architecture

## Overview

This document describes how data flows through the Claude Code Orchestrator system from user input to task completion.

## Main Orchestration Loop

### Sequence Diagram

```
User → Orchestrator → TaskScheduler → PromptGenerator → Agent → FileWatcher
         ↓                                                         ↓
   StateManager ←── DecisionEngine ←── QualityController ←── ResponseValidator
```

### Detailed Flow

```
1. User initiates task
   ├─→ CLI validates input
   └─→ Create task in StateManager

2. Orchestrator main loop
   ├─→ Check for breakpoints (BreakpointManager)
   │   └─→ If triggered: pause and wait for user
   │
   ├─→ Get next task (TaskScheduler)
   │   ├─→ Resolve dependencies
   │   ├─→ Check priorities
   │   └─→ Return highest priority ready task
   │
   ├─→ Generate prompt (PromptGenerator)
   │   ├─→ Load template
   │   ├─→ Gather context from StateManager
   │   ├─→ Estimate tokens
   │   ├─→ Trim context if needed
   │   └─→ Render final prompt
   │
   ├─→ Send to agent (via AgentPlugin)
   │   ├─→ Agent executes task
   │   ├─→ FileWatcher tracks changes
   │   └─→ Agent returns response
   │
   ├─→ Validate response (ResponseValidator)
   │   ├─→ Check completeness
   │   ├─→ Verify format
   │   ├─→ If invalid: retry or breakpoint
   │   └─→ If valid: proceed
   │
   ├─→ Check quality (QualityController)
   │   ├─→ Local LLM evaluates correctness
   │   ├─→ Run tests if applicable
   │   ├─→ Score quality
   │   ├─→ If low quality: retry or breakpoint
   │   └─→ If good quality: proceed
   │
   ├─→ Make decision (DecisionEngine)
   │   ├─→ Calculate confidence score
   │   ├─→ Determine next action:
   │   │   ├─→ Task complete: mark done
   │   │   ├─→ Needs refinement: retry with feedback
   │   │   ├─→ Uncertain: trigger breakpoint
   │   │   └─→ Continue: next iteration
   │   └─→ Update state
   │
   └─→ Persist everything (StateManager)
       ├─→ Save interaction
       ├─→ Update task status
       ├─→ Record file changes
       └─→ Checkpoint state

3. Loop continues or stops
   ├─→ If breakpoint: wait for user input
   ├─→ If task complete: move to next task
   ├─→ If error: handle and possibly escalate
   └─→ If queue empty: done
```

## Component Interactions

### Task Creation Flow

```
User Input
    ↓
CLI validates and parses
    ↓
StateManager.create_task()
    ├─→ Validate task data
    ├─→ Assign ID
    ├─→ Set initial status (pending)
    ├─→ Detect dependencies
    └─→ Persist to database
    ↓
TaskScheduler notified
    └─→ Update priority queue
```

### Prompt Generation Flow

```
Task from Scheduler
    ↓
PromptGenerator.generate()
    ├─→ Load template for task type
    │   └─→ Jinja2 template from config
    │
    ├─→ Gather context
    │   ├─→ Task description
    │   ├─→ Recent interactions (from StateManager)
    │   ├─→ Relevant files (from FileWatcher)
    │   ├─→ Project context
    │   └─→ Constraints/requirements
    │
    ├─→ Estimate tokens (via LLMPlugin)
    │   ├─→ Count current content
    │   └─→ Check against limit
    │
    ├─→ Trim if needed (ContextManager)
    │   ├─→ Prioritize recent interactions
    │   ├─→ Summarize older context
    │   └─→ Keep requirements intact
    │
    └─→ Render final prompt
        └─→ Return to Orchestrator
```

### Agent Execution Flow

```
Prompt from PromptGenerator
    ↓
AgentPlugin.send_prompt()
    ├─→ Establish/verify connection
    │   └─→ If unhealthy: reconnect or fail
    │
    ├─→ Start FileWatcher monitoring
    │   ├─→ Record baseline file hashes
    │   └─→ Begin watching workspace
    │
    ├─→ Send prompt to agent process
    │   ├─→ Via SSH (ClaudeCodeSSHAgent)
    │   ├─→ Via Docker API (ClaudeCodeDockerAgent)
    │   └─→ Via subprocess (LocalAgent)
    │
    ├─→ Monitor output
    │   ├─→ OutputMonitor tracks stdout/stderr
    │   ├─→ Detect completion indicators
    │   └─→ Detect errors
    │
    ├─→ Wait for completion
    │   ├─→ With timeout
    │   └─→ Track file changes in background
    │
    └─→ Return response
        ├─→ Agent's text output
        └─→ File changes detected
```

### Validation Flow

```
Agent Response
    ↓
ResponseValidator.validate()
    ├─→ Check completeness
    │   ├─→ Response not truncated?
    │   ├─→ Code blocks properly closed?
    │   ├─→ Required sections present?
    │   └─→ Valid: proceed, Invalid: fail
    │
    └─→ If valid: pass to QualityController
    ↓
QualityController.check_quality()
    ├─→ Local LLM evaluates response
    │   ├─→ Prompt: "Does this meet requirements?"
    │   ├─→ LLM scores 0-100
    │   └─→ Extract reasoning
    │
    ├─→ Run tests if applicable
    │   ├─→ Execute test suite
    │   ├─→ Collect results
    │   └─→ Factor into score
    │
    ├─→ Check file changes
    │   ├─→ Expected files created?
    │   ├─→ No unexpected changes?
    │   └─→ Files have valid syntax?
    │
    ├─→ Calculate final quality score
    │   ├─→ Weight: LLM 40%, tests 40%, files 20%
    │   └─→ Threshold: 70 to pass
    │
    └─→ Return quality result
        ├─→ pass/fail
        ├─→ score
        └─→ reasoning
```

### Decision Making Flow

```
Validation Result + Quality Result
    ↓
DecisionEngine.decide_next_action()
    ├─→ Calculate confidence
    │   ├─→ Factor validation status
    │   ├─→ Factor quality score
    │   ├─→ Factor agent health
    │   ├─→ Factor retry count
    │   └─→ Score: 0-100
    │
    ├─→ Determine action
    │   ├─→ Confidence ≥80: task complete
    │   ├─→ Confidence 50-79: continue iteration
    │   ├─→ Confidence 30-49: retry with feedback
    │   └─→ Confidence <30: trigger breakpoint
    │
    ├─→ Generate explanation
    │   └─→ Why this decision was made
    │
    └─→ Return decision
        ├─→ action (complete/continue/retry/breakpoint)
        ├─→ confidence
        ├─→ explanation
        └─→ suggested_prompt (if retry)
```

### State Persistence Flow

```
Any State Change
    ↓
StateManager.update()
    ├─→ Acquire lock (thread-safe)
    │
    ├─→ Begin transaction
    │   ├─→ Validate state change
    │   ├─→ Update in-memory cache
    │   └─→ Write to database
    │
    ├─→ Emit event (for monitoring)
    │   └─→ Subscribers notified
    │
    ├─→ Commit transaction
    │   ├─→ Success: update committed
    │   └─→ Failure: rollback
    │
    └─→ Release lock
    ↓
State Consistent
```

## Task State Machine

```
[PENDING] ─────────→ [IN_PROGRESS]
    ↑                     │
    │                     ├─→ [VALIDATING]
    │                     │         │
    │                     │         ├─→ [QUALITY_CHECK]
    │                     │         │         │
    │                     │         │         ├─→ [COMPLETED]
    │                     │         │         │
    │                     │         │         └─→ [RETRY_NEEDED] ──→ [IN_PROGRESS]
    │                     │         │
    │                     │         └─→ [FAILED]
    │                     │
    │                     └─→ [BREAKPOINT]
    │                           │
    └───────────────────────────┘ (user resolves)
```

### State Transitions

| From | To | Trigger |
|------|-----|---------|
| PENDING | IN_PROGRESS | Scheduler selects task |
| IN_PROGRESS | VALIDATING | Agent returns response |
| VALIDATING | QUALITY_CHECK | Validation passes |
| VALIDATING | FAILED | Validation fails (max retries) |
| VALIDATING | RETRY_NEEDED | Validation fails (retries remain) |
| QUALITY_CHECK | COMPLETED | Quality sufficient, confidence high |
| QUALITY_CHECK | RETRY_NEEDED | Quality low but improvable |
| QUALITY_CHECK | BREAKPOINT | Uncertain, needs human input |
| QUALITY_CHECK | FAILED | Quality too low (max retries) |
| RETRY_NEEDED | IN_PROGRESS | Retry with feedback |
| BREAKPOINT | PENDING | User provides guidance |
| BREAKPOINT | FAILED | User cancels task |

## File Change Tracking

```
Agent Modifies Files
    ↓
FileWatcher detects change (via watchdog)
    ├─→ Debounce rapid changes (wait 500ms)
    │
    ├─→ Calculate file hash
    │   └─→ Compare with previous hash
    │
    ├─→ Determine change type
    │   ├─→ New file: created
    │   ├─→ Changed hash: modified
    │   └─→ File gone: deleted
    │
    ├─→ Record change
    │   ├─→ Timestamp
    │   ├─→ Path
    │   ├─→ Hash
    │   ├─→ Change type
    │   └─→ Size
    │
    └─→ Persist to StateManager
        └─→ Associated with current interaction
```

## Breakpoint Flow

```
Breakpoint Triggered
    ↓
BreakpointManager.trigger()
    ├─→ Pause orchestration loop
    │
    ├─→ Collect context
    │   ├─→ Why triggered (low confidence, etc.)
    │   ├─→ Current task state
    │   ├─→ Recent interactions
    │   ├─→ Suggested actions
    │   └─→ Decision reasoning
    │
    ├─→ Notify user
    │   ├─→ CLI prompt
    │   ├─→ Display context
    │   └─→ Request input
    │
    ├─→ Wait for user decision
    │   ├─→ Continue: resume with guidance
    │   ├─→ Retry: try again with new prompt
    │   ├─→ Cancel: mark task failed
    │   └─→ Modify: change task parameters
    │
    ├─→ Record resolution
    │   └─→ Persist user decision and reasoning
    │
    └─→ Resume orchestration
        └─→ Apply user's decision
```

## Error Recovery Flow

```
Error Occurs
    ↓
Exception Handler
    ├─→ Categorize error
    │   ├─→ Transient (network glitch)
    │   ├─→ Recoverable (agent crash)
    │   └─→ Fatal (invalid config)
    │
    ├─→ Attempt recovery
    │   ├─→ Transient: retry with backoff
    │   │   ├─→ Retry 1: wait 1s
    │   │   ├─→ Retry 2: wait 2s
    │   │   ├─→ Retry 3: wait 4s
    │   │   └─→ Max retries: escalate
    │   │
    │   ├─→ Recoverable: checkpoint + restart
    │   │   ├─→ Save current state
    │   │   ├─→ Attempt agent reconnect
    │   │   └─→ Resume from checkpoint
    │   │
    │   └─→ Fatal: trigger breakpoint
    │       └─→ Require user intervention
    │
    └─→ Log error details
        ├─→ Error type
        ├─→ Context
        ├─→ Recovery attempted
        └─→ Outcome
```

## Performance Optimization

### Caching Strategy

```
Request for Context
    ↓
ContextManager checks cache
    ├─→ Cache hit: return cached data
    │   └─→ Update access time
    │
    └─→ Cache miss: fetch data
        ├─→ Query StateManager
        ├─→ Process/summarize if needed
        ├─→ Store in cache (with TTL)
        └─→ Return data
```

### Parallel Operations

Where possible, operations run concurrently:

```
Task Selected
    ↓
[Gather Context] ─┐
[Check Agent Health] ─┼─→ When all complete → Generate Prompt
[Load Template] ─┘

Agent Responding
    ↓
[Monitor Output] ─┐
[Watch Files] ─────┼─→ Both run concurrently
[Track Timing] ────┘
```

## Data Storage

### Database Schema (High-Level)

```
projects
    ├─→ tasks (1:many)
    │     ├─→ interactions (1:many)
    │     │     └─→ file_changes (1:many)
    │     └─→ checkpoints (1:many)
    │
    └─→ breakpoints (1:many)
```

### State Checkpointing

```
Before Risky Operation
    ↓
StateManager.create_checkpoint()
    ├─→ Snapshot current state
    │   ├─→ All tasks
    │   ├─→ All interactions
    │   ├─→ File hashes
    │   └─→ Metadata
    │
    ├─→ Serialize to JSON
    │
    └─→ Store in database
        └─→ Tagged with timestamp + reason
```

## Monitoring and Metrics

### Metrics Collection

```
Operation Completes
    ↓
Record Metrics
    ├─→ Duration
    ├─→ Success/Failure
    ├─→ Confidence Score
    ├─→ Resource Usage
    └─→ Store in StateManager

Periodically
    ↓
Aggregate Metrics
    ├─→ Success rate over time
    ├─→ Average confidence
    ├─→ Breakpoint frequency
    ├─→ Performance percentiles
    └─→ Generate reports
```

---

**Note**: Detailed implementations in Milestones 1-6. This document describes the target architecture.
