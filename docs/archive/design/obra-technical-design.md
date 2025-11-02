# Obra Technical Design Document
**Virtual Developer (VD) Feature Specification**

## Terminology
- **VD (Virtual Developer):** Local LLM orchestration layer (Obra product itself)
- **rAI (Remote AI):** External LLM APIs (Claude, GPT-4, Gemini, etc.)
- **Agent:** Specialized VD instance or context for specific tasks

---

## Feature Priority Framework
- **P0 (MVP - Alpha Program):** Must-have for first customer deployments
- **P1 (Beta - Months 7-12):** Needed for paid launch and scale
- **P2 (Future - Year 2+):** Advanced features for enterprise maturity

---

## 1. CORE ORCHESTRATION LAYER

### 1.1 Task Delegation & Routing **[P0]**
**Description:** Intelligence to decide which work goes to VD (local) vs rAI (remote)

**Key Capabilities:**
- Analyze task complexity and resource requirements
  - Estimate token count, time, computational cost
  - Assess task types: reasoning/validation (VD) vs generation (rAI)
- Decision-making framework
  - Define delegation criteria (complexity, urgency, cost threshold)
  - Route validation, testing interpretation, pattern matching → VD
  - Route code generation, complex reasoning, creative tasks → rAI
  - Hybrid tasks: VD prepares context, rAI generates, VD validates
- Performance tracking
  - Log delegation decisions and outcomes
  - ML-based optimization of routing over time (P1)

**Implementation Notes:**
- Start with rule-based routing (P0)
- Evolve to learned routing model based on success metrics (P1)

---

### 1.2 Prompt Orchestration & Context Management **[P0]**
**Description:** VD generates optimized prompts for rAI with appropriate context

**Key Capabilities:**
- Context extraction from codebase
  - Identify relevant files, dependencies, types, patterns
  - Trim context to fit rAI token limits
  - Include coding standards, test templates, team conventions
- Prompt template library
  - Pre-optimized prompts for common tasks (feature creation, bug fixing, refactoring)
  - Include few-shot examples from team's codebase
  - Format responses for structured parsing (JSON, XML)
- Batching & optimization
  - Group related tasks to minimize API calls
  - Reuse context across multiple prompts
  - Implement prompt caching strategies

**rAI Response Instructions:** **[P0]**
- Require structured response formats (JSON/XML)
- Request workplan optimization for parallel execution
- Include task breakdown with dependencies
- Specify test requirements for each component
- Request error handling and edge case coverage

---

### 1.3 VD Validation & Quality Control **[P0]**
**Description:** Local LLM validates rAI outputs before testing

**Key Capabilities:**
- Pattern compliance checking
  - Compare generated code against existing codebase patterns
  - Flag style violations, anti-patterns, security issues
- Syntax & type validation
  - Real-time syntax checking during streaming responses
  - Type safety analysis (TypeScript, Python type hints, etc.)
- Completeness checks
  - Verify test coverage requirements met
  - Ensure error handling present
  - Check documentation/comments included
- Bug pattern detection
  - Common mistakes: null checks, resource leaks, race conditions
  - Language-specific gotchas

**VD Analysis Template:** **[P0]**
- Score rAI response on multiple dimensions (0-100)
  - Correctness: Syntax, logic, completeness
  - Quality: Patterns, style, maintainability
  - Safety: Security, error handling, edge cases
  - Testability: Coverage, test quality
- Generate structured feedback for refinement loops
- Decision: Approve → Testing OR Refine → New rAI prompt OR Escalate → Human review

---

## 2. RELIABILITY & RECOVERY

### 2.1 State Management & Auto-Save **[P0]**
**Description:** Continuous project state persistence to enable recovery

**Key Capabilities:**
- Auto-save at regular intervals (every 30 seconds or after major events)
  - VD-rAI conversation history with full context
  - Code files and configuration (git-tracked)
  - Test results, logs, metrics
  - Current task state and progress
- Checkpoint system
  - Mark "known good states" after successful tests
  - Enable rollback to last stable checkpoint
  - Snapshot before risky operations (major refactors)

---

### 2.2 Crash & Failure Recovery **[P1]**
**Description:** Automatic detection and recovery from system failures

**Key Capabilities:**
- Crash detection
  - Monitor VD/rAI process health
  - Detect hung processes, timeouts, OOM errors
  - Track external service failures (rAI API outages)
- Automatic restart
  - Restore from last checkpoint
  - Resume interrupted tasks seamlessly
  - Notify user of recovery with summary
- Root cause analysis
  - Parse logs and error messages
  - Identify crash patterns (e.g., context overflow, API rate limits)
  - Implement preventive measures (better chunking, rate limiting)

---

### 2.3 Error Recovery & Escalation **[P0]**
**Description:** Intelligent handling of task failures with progressive escalation

**Key Capabilities:**
- Escalation thresholds
  - Define failure criteria (e.g., 3 failed attempts, 10 min spent, validation score < 30)
  - Track attempt history per task
- Escalation protocols
  - **Level 1:** Retry with improved prompt (VD adds more context, examples)
  - **Level 2:** Switch to more capable rAI model (GPT-4 → GPT-4 Turbo, Claude Sonnet → Opus)
  - **Level 3:** Increase token budget for deeper reasoning
  - **Level 4:** Human operator notification with detailed context
- Escalation tracking
  - Log all escalations with reasoning
  - Analyze escalation patterns to improve VD routing
  - Cost tracking for escalated tasks

---

## 3. PERFORMANCE & RESOURCE MANAGEMENT

### 3.1 Local Hardware Optimization **[P1]**
**Description:** VD adapts to available hardware for optimal performance

**Key Capabilities:**
- Hardware detection
  - Read CPU specs (cores, speed)
  - Detect GPU availability (CUDA, ROCm, Metal)
  - Check RAM size, disk speed, network bandwidth
- Auto-configuration
  - CPU-only mode: Smaller VD model, sequential processing
  - GPU mode: Larger VD model, batch processing
  - Adjust VD batch size, context length based on RAM
  - Set thread/process limits to avoid system overload
- Real-time monitoring
  - Track CPU/GPU utilization, memory usage, disk I/O
  - Throttle VD workload if system resources constrained
  - Warn user if hardware insufficient for project scale
- Performance recommendations **[P2]**
  - Log bottlenecks (e.g., "GPU limited: consider RTX 4090 for 2x speedup")
  - Suggest hardware upgrades with ROI analysis

**Deployment Options:**
- **Low-cost tier:** CPU-only, smaller VD model (Llama 3.1 8B)
- **Standard tier:** Consumer GPU (RTX 4090), medium VD model (Llama 3.1 70B)
- **Enterprise tier:** Data center GPU (H100), large VD model + multi-agent parallelism

---

### 3.2 Agent Architecture & Parallelism **[P1 → P2]**
**Recommendation:** Start simple, evolve to parallel

#### Phase 1 (P1): Single VD Instance with Context Switching
- Single VD process with specialized prompt contexts
- "Modes": Design, Coding, Testing, Debugging, Documentation
- Sequential execution with context reuse
- **Pros:** Simpler, lower resource usage, easier debugging
- **Cons:** No true parallelism, context switching overhead

#### Phase 2 (P2): Multi-Agent Parallel Execution
- Separate VD agent processes for independent tasks
- Agent types:
  - **Design Agent:** Architecture planning, task breakdown
  - **Coding Agent:** Code generation orchestration (VD → rAI → VD validation)
  - **Testing Agent:** Test execution, result interpretation
  - **Debugging Agent:** Failure analysis, fix generation
  - **Documentation Agent:** README, comments, API docs
  - **PM Agent:** Progress tracking, reporting, resource allocation
- Parallel deployment
  - VD analyzes workplan, identifies independent tasks
  - Spawn agents for parallel execution (e.g., 3 coding agents for 3 modules)
  - Isolate testing to prevent cross-contamination
  - PM Agent coordinates, aggregates results
- Agent lifecycle management
  - Creation: Spawn with task-specific context
  - Monitoring: Track progress, resource usage
  - Termination: Clean shutdown, result collection
  - Error handling: Restart failed agents, escalate persistent failures

**Implementation Path:**
- Alpha: Single-instance VD only (P0)
- Beta: Add multi-agent for parallel testing (P1)
- Scale: Full multi-agent architecture (P2)

---

## 4. MONITORING & OBSERVABILITY

### 4.1 Structured Logging **[P0]**
**Description:** Comprehensive, LLM-parseable logs for debugging and analysis

**Key Capabilities:**
- Multi-level logging
  - **Project logs:** High-level progress, milestones, errors
  - **VD logs:** Validation decisions, routing, escalations
  - **rAI logs:** Prompts sent, responses received, token usage
  - **System logs:** Hardware metrics, resource usage, crashes
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Structured format (JSON) for machine parsing
  - Timestamp, log level, component, message, context (file, task ID)
  - Include full prompt/response for rAI interactions (privacy-safe)
- Log rotation & archival
  - Rotate daily or at size limit (100MB)
  - Compress and archive old logs
  - Retain recent logs in-memory for fast VD access

**Critical for VD:**
- VD actively parses logs to diagnose issues
- Automatic log analysis after test failures
- Pattern recognition across logs to identify recurring issues
- Generate human-readable summaries from structured logs

---

### 4.2 Metrics & Reporting **[P0 → P1]**
**Description:** Track project health and Obra value delivery

#### Developer-Facing Metrics (P0):
- Task progress (intent → design → code → test → complete)
- Current blockers and errors
- Estimated completion time
- Cost incurred (API tokens, compute time)

#### Enterprise Metrics (P1):
- **Cost savings:**
  - Total API spend vs baseline (pre-Obra)
  - Local (VD) vs remote (rAI) token split
  - Cost per feature, cost per line of code
- **Productivity gains:**
  - Feature cycle time (design → production)
  - Developer idle time (waiting for VD/rAI)
  - Prompt iteration count (target: <2.5 avg)
- **Quality indicators:**
  - Test pass rate
  - Bug rate per 1,000 LOC
  - Code review rejection rate
  - Production incidents attributed to AI-generated code
- **VD performance:**
  - Validation accuracy (false positives/negatives)
  - Escalation rate
  - rAI routing efficiency
- **Design quality:**
  - Task clarity score (VD assesses if intent is specific enough)
  - Chunking optimization (are tasks right-sized for rAI?)
  - Rework rate (how often do tasks need re-planning?)

#### Automated Status Reports (P1):
- Daily digest: What was completed, what's pending, issues, costs, next steps
- Weekly summary: Progress vs goals, cost trends, productivity metrics
- Milestone reports: Feature delivery retrospectives

---

### 4.3 Real-Time Dashboard **[P2]**
**Description:** Visual project status (GUI, much later)

**Dashboard Elements:**
- Hierarchical task view
  - Top level: Design intent
  - Mid level: Modules/features
  - Bottom level: Individual tasks
- Status indicators (color-coded pips)
  - Intent defined ✓
  - Implementation plan ✓
  - Test plan ✓
  - Code developed ✓
  - Tests developed ✓
  - Tests run ✓
  - Tests passed ✓
  - Debugging (if needed)
  - Complete ✓
- Agent activity view (if multi-agent enabled)
- Resource usage graphs (CPU, GPU, memory, API spend)
- Recent logs and alerts

---

## 5. TESTING & QUALITY ASSURANCE

### 5.1 Automated Testing Framework **[P0]**
**Description:** Comprehensive testing orchestrated by VD

**Test Types:**
- **Unit tests** (P0): Function-level correctness
- **Integration tests** (P0): Module interactions
- **System tests** (P1): End-to-end workflows
- **Regression tests** (P0): Ensure changes don't break existing features
- **Code coverage analysis** (P1): Track untested code paths
- **Performance tests** (P1): Latency, throughput benchmarks
- **Security tests** (P2): Vulnerability scanning, fuzzing
- **Fuzz testing** (P2): Random input generation

**VD Role in Testing:**
- Generate test plans alongside code
- Write tests (or orchestrate rAI to write tests)
- Execute tests automatically after each code change
- **Interpret results** (key VD responsibility)
  - Parse test output, stack traces, error messages
  - Diagnose root causes of failures
  - Generate targeted debugging prompts for rAI
  - Decide: retry, escalate, or mark as blocker

**LLM-Optimized Test Instructions (P1):**
- Test output formatted for LLM parsing (structured JSON/XML)
- Include expected vs actual results
- Provide file/line numbers for failures
- Suggest likely causes based on error patterns

---

## 6. ADVANCED FEATURES (FUTURE)

### 6.1 VD Self-Improvement **[P2]**
**Description:** VD learns from project history to improve performance

**Key Capabilities:**
- Prompt template optimization
  - Track which prompts yield best rAI results
  - A/B test variations, refine based on success rates
- Validation model tuning
  - Fine-tune local VD model on customer codebase patterns
  - Improve pattern matching, bug detection accuracy
- Routing intelligence
  - ML model to predict optimal VD vs rAI routing
  - Learn from escalation patterns and cost/quality tradeoffs

---

### 6.2 Multi-Project Knowledge Sharing **[P2]**
**Description:** VD learns patterns across multiple projects (within org)

**Key Capabilities:**
- Shared pattern library
  - Common architectural patterns (microservices, MVC, etc.)
  - Language idioms and best practices
  - Company-wide coding standards
- Cross-project insights
  - "Project A solved similar problem with approach X"
  - Reusable components and utilities
- Privacy controls
  - Project isolation vs knowledge sharing (customer configurable)
  - Sanitize sensitive data in shared learnings

---

### 6.3 Human-in-the-Loop Refinement **[P1]**
**Description:** VD learns from developer feedback

**Key Capabilities:**
- Feedback collection
  - Developer approves/rejects VD decisions
  - Annotations on code quality, test coverage
  - Explicit corrections ("This should use pattern X instead")
- Feedback integration
  - VD updates local knowledge base
  - Adjusts validation thresholds
  - Refines prompt templates
- Feedback analytics
  - Track common rejection reasons
  - Identify VD blind spots
  - Prioritize improvement areas

---

## 7. ADDITIONAL FEATURE RECOMMENDATIONS

### 7.1 Budget Management & Cost Controls **[P0]**
**Description:** Prevent runaway costs, enforce spending limits

**Key Capabilities:**
- Budget configuration
  - Set max API spend per task, per day, per month
  - Token budgets per rAI interaction
  - Time limits per task (prevent infinite loops)
- Cost tracking
  - Real-time API cost accumulation
  - Projected costs for queued tasks
  - Alerts when approaching budget limits
- Cost optimization
  - VD proposes cheaper alternatives when budget tight
  - Suggest using smaller models or more local processing
  - Batch tasks to minimize API calls

---

### 7.2 Compliance & Security **[P1 → P2]**
**Description:** Enterprise-grade security and audit capabilities

#### Key Capabilities (P1):
- Audit logging
  - All VD decisions, rAI interactions, code changes
  - Tamper-proof logs for compliance
- Access controls
  - Role-based permissions (who can approve, deploy)
  - API key management
- Data privacy
  - Configurable data retention policies
  - Sanitize PII before sending to rAI
  - Support for air-gapped environments (no rAI, VD only)

#### Advanced Security (P2):
- Security scanning
  - VD checks generated code for vulnerabilities
  - Integration with SAST/DAST tools
- Secrets management
  - Detect hardcoded secrets in rAI outputs
  - Integration with vault systems
- Compliance reporting
  - SOC 2, HIPAA, FedRAMP audit reports
  - Track all code provenance (human vs AI)

---

### 7.3 Integration Ecosystem **[P1]**
**Description:** Connect Obra to existing developer tools

**Key Integrations:**
- **Version control:** GitHub, GitLab, Bitbucket
  - Automatic PR creation
  - Commit message generation
- **Project management:** Jira, Linear, Asana
  - Task import (pull requirements into Obra)
  - Status sync (update tickets automatically)
- **CI/CD:** Jenkins, CircleCI, GitHub Actions
  - Trigger pipelines after Obra completes features
  - Ingest build/test results
- **IDEs:** VSCode, JetBrains, Vim
  - Obra status indicators in IDE
  - One-click task submission to Obra
- **Observability:** Datadog, Sentry
  - Production error feedback loop into Obra

---

### 7.4 Collaboration Features **[P2]**
**Description:** Multi-developer teamwork on Obra projects

**Key Capabilities:**
- Shared project state
  - Multiple developers work on same project
  - Conflict resolution when tasks overlap
- Task assignment
  - Distribute work among team members and VD
  - Track who approved which AI-generated changes
- Code review workflows
  - VD generates PR, assigns reviewers
  - Integrates review feedback into future generations
- Team learning
  - One developer's corrections benefit entire team
  - Shared validation rules and preferences

---

## 8. IMPLEMENTATION PRIORITIES

### Alpha Program (Months 1-6) - MVP Features

#### Must Build (P0):
1. Core orchestration: VD → rAI → VD validation loop
2. Task delegation framework (rule-based)
3. Prompt optimization and context management
4. VD validation scoring and feedback
5. Error recovery and escalation (Levels 1-3)
6. State management and auto-save
7. Structured logging (project, VD, rAI)
8. Basic automated testing (unit, integration, regression)
9. Test result interpretation by VD
10. Basic metrics (cost, progress, errors)
11. Budget controls (cost limits, time limits)
12. CLI interface

#### Success Criteria:
- 60-75% API cost reduction vs all-remote workflow
- <2.5 average prompt iterations per feature
- VD validation catches 80%+ of bugs before human review

---

### Beta / Paid Launch (Months 7-12)

#### Add (P1):
1. Local hardware optimization and auto-configuration
2. Multi-agent architecture (parallel testing)
3. Crash detection and automatic recovery
4. Advanced metrics and enterprise reporting
5. Automated status reports (daily, weekly)
6. IDE integrations (VSCode, JetBrains)
7. Git integration (PR creation, commit messages)
8. Project management integration (Jira, Linear)
9. Human feedback loop and learning
10. Code coverage and performance testing
11. LLM-optimized test output formats
12. Web dashboard (basic)

---

### Scale (Year 2+)

#### Add (P2):
1. Full multi-agent parallelism with PM agent
2. VD self-improvement (prompt tuning, routing ML)
3. Multi-project knowledge sharing
4. Advanced hardware recommendations
5. GUI with hierarchical task visualization
6. Security scanning and compliance features
7. Air-gapped deployment mode (no rAI)
8. Collaboration features (multi-developer)
9. Advanced testing (fuzzing, security)
10. Custom VD model fine-tuning per customer

---

## 9. OPEN DESIGN QUESTIONS

### Question 1: Agent Architecture Trade-offs
**Decision needed:** Single VD instance vs multi-agent from start?

**Recommendation:** 
- **Alpha:** Single-instance only (simpler, faster to build)
- **Beta:** Add multi-agent for parallel testing (proven value)
- **Scale:** Full multi-agent for all task types

**Rationale:** Validate core orchestration value before investing in parallelism complexity.

---

### Question 2: VD Model Selection
**Decision needed:** Which local LLM for VD?

**Options:**
- **Llama 3.1 70B:** Strong reasoning, good balance of quality/speed
- **Qwen 2.5 72B:** Competitive quality, slightly faster inference
- **Mixtral 8x22B:** MoE efficiency, lower memory footprint
- **Custom fine-tuned model:** Optimize for validation/routing tasks

**Recommendation:** Start with Llama 3.1 70B (proven, well-documented), offer Qwen as alternative. Explore fine-tuning in Year 2.

---

### Question 3: Context Window Strategy
**Decision needed:** How to handle projects larger than VD/rAI context windows?

**Options:**
- **Chunking:** Break project into overlapping chunks (risk: loss of coherence)
- **RAG:** Vector DB of codebase, retrieve relevant context (complex infrastructure)
- **Hierarchical planning:** VD manages high-level plan, rAI handles modules (scales well)

**Recommendation:** Hierarchical planning for Alpha (aligns with orchestration model), add RAG in Beta if needed.

---

### Question 4: rAI Provider Strategy
**Decision needed:** Support multiple rAI providers or single default?

**Recommendation:**
- **Alpha:** Support Claude (Anthropic) and GPT-4 (OpenAI) - cover 90% of market
- **Beta:** Add Gemini (Google), open-source models (Llama, Mistral) for air-gapped deployments
- **Abstraction layer:** VD uses provider-agnostic prompt format, translates to provider-specific APIs

**Rationale:** Multi-provider is key differentiator vs locked-in tools (Copilot, Cursor).

---

## 10. NEXT STEPS

1. **Validate priorities** with technical co-founder / lead engineer
2. **Build proof-of-concept** for core loop (intent → VD → rAI → VD validation → testing)
3. **Select VD model** and benchmark performance on sample codebases
4. **Define MVP scope** for first alpha customer (3-month timeline)
5. **Design API contracts** between VD and rAI, VD and external systems
6. **Set up infrastructure** for logging, metrics, state management

---

## Summary of Key Recommendations

1. **Start simple, evolve complexity:** Single VD instance → Multi-agent over time
2. **Prioritize reliability:** State management, logging, error recovery are P0
3. **Metrics matter:** Build cost/productivity tracking from day one to prove ROI
4. **Budget controls are critical:** Prevent runaway costs that could kill customer trust
5. **Testing interpretation is VD's killer feature:** This is where VD adds most value over raw rAI
6. **Multi-provider support:** Key differentiator vs competitors
7. **Learning loops:** Human feedback and VD self-improvement are long-term moats

---

**Document Version:** 1.0 - Technical Design  
**Last Updated:** November 2025  
**Status:** Draft for Engineering Review
