# Obra Product Roadmap

**Last Updated**: 2025-11-11
**Current Version**: v1.4.0 (Project Infrastructure Maintenance System)
**Strategic Focus**: Solo/small team developer workflow optimization

---

## Vision & Strategic Direction

**Mission**: Empower solo developers and small teams with AI orchestration that enhances productivity through validated best practices, security-first design, and intuitive workflows.

**Differentiators**:
- Industry-leading validation pipeline (ResponseValidator → QualityController → ConfidenceScorer)
- Per-iteration session model (eliminates session lock bugs)
- Empirically validated prompt optimization (35% token efficiency proven via A/B testing)
- Agile work hierarchy (Epic/Story/Task/Subtask) with full database support
- Comprehensive testing (91% coverage, 790+ tests)

**Target Users**:
- **Primary**: Solo developers, indie hackers, small startups (1-5 devs)
- **Secondary**: Small dev teams at larger companies (5-15 devs)
- **Future**: Enterprise teams (defer to v2.0+ based on demand)

---

## Release History

### v1.0.0 - Foundation (Q3 2024)
- ✅ Plugin system (AgentPlugin, LLMPlugin)
- ✅ StateManager (single source of truth)
- ✅ Basic orchestration (plan → execute → validate)
- ✅ SQLite database with models
- ✅ CLI interface

### v1.1.0 - Validation Pipeline (Q4 2024)
- ✅ ResponseValidator (format/completeness checks)
- ✅ QualityController (correctness validation)
- ✅ ConfidenceScorer (hybrid heuristic + LLM)
- ✅ DecisionEngine (proceed/retry/escalate)
- ✅ Test coverage ≥85%

### v1.2.0 - Session Management & Headless Mode (Q4 2024)
- ✅ Per-iteration session model (ADR-007)
- ✅ SessionManager with refresh thresholds
- ✅ Headless mode (`--print`, `--dangerously-skip-permissions`)
- ✅ ContextManager for state continuity
- ✅ FileWatcher for change tracking

### v1.3.0 - Core Enhancements (Q1 2025)
- ✅ Retry logic with exponential backoff (ADR-008)
- ✅ Task dependency system (ADR-009)
- ✅ Git auto-integration (ADR-010)
- ✅ Configuration profiles (6 presets)
- ✅ Agile work hierarchy (Epic/Story/Task/Subtask, ADR-013)
- ✅ Interactive orchestration (6 checkpoint injection points, ADR-011)

### v1.4.0 - Project Infrastructure Maintenance (Q1 2025) **[CURRENT]**
- ✅ Natural language command interface (ADR-014)
- ✅ Project infrastructure maintenance system (ADR-015)
- ✅ NL command validation and execution
- ✅ Interactive UX improvements (default to orchestrator mode)
- ✅ Test coverage → 91%

---

## Upcoming Releases

### v1.5.0 - Security & Structured Outputs **[NEXT - Target: March 2026]**

**Theme**: Production security hardening + enhanced prompt engineering

**Priority**: 🔴 P0-CRITICAL security items MUST ship before wider distribution

#### P0-CRITICAL Security (3 weeks)
- [ ] **EP-001**: Prompt injection detection patterns [from BP guide v2.2 §8.2]
  - Pattern-based detection (ignore instructions, special tokens, etc.)
  - Severity classification (LOW/MEDIUM/HIGH/CRITICAL)
  - Integration with StructuredPromptBuilder, CommandProcessor
  - **Impact**: Prevents malicious prompt hijacking
  - **Effort**: M (3-5 days)

- [ ] **EP-002**: Input sanitization [from BP guide v2.2 §8.2]
  - Remove special tokens, redact suspicious patterns
  - Configurable modes (remove/redact/escape)
  - Defense-in-depth with EP-001
  - **Impact**: Neutralizes detected injections
  - **Effort**: S (1-2 days)

- [ ] **EP-003**: Tool execution allowlisting [from BP guide v2.2 §8.3]
  - Policy framework (ALLOWED/RESTRICTED/REVIEW_REQUIRED/FORBIDDEN)
  - Interactive confirmation for restricted tools
  - Audit trail for all tool executions
  - **Impact**: Prevents destructive operations
  - **Effort**: M (3-5 days)

- [ ] **EP-004**: Tool output sanitization [from BP guide v2.2 §8.4]
  - PII detection (emails, SSNs, phone numbers, addresses)
  - Secret detection (API keys, passwords, tokens, AWS keys)
  - Redaction before logging/display
  - **Impact**: Prevents data leaks
  - **Effort**: S (1-2 days)

#### P1-HIGH Structured Outputs (5-7 weeks)

- [ ] **EP-005**: Plan manifest schema implementation [from BP guide v2.2 §3]
  - JSON schema matching guide v2.2 specification
  - Plan generator from Epic/Story/Task models
  - Schema validator + versioning
  - Machine-readable plans enable advanced automation
  - **Impact**: Industry-standard format, better tooling
  - **Effort**: L (1-2 weeks)

- [ ] **EP-006**: Canonical 11-section prompt structure [from BP guide v2.2 §2]
  - Align StructuredPromptBuilder with guide's canonical structure
  - Sections: Identity, Objective, Context, Reasoning, Deliverables, Acceptance, Planning, Execution, Error Handling, Observability, Security
  - **Impact**: Improved Claude response quality (estimated 20-30%)
  - **Effort**: M (3-5 days)

- [ ] **EP-007**: Specialized task templates [from BP guide v2.2 §13]
  - **Frontend UI Feature**: React/Vue, accessibility, responsive design
  - **API Endpoint Development**: REST/GraphQL, validation, error handling
  - **Bug Fix**: Reproduction, root cause, fix, regression tests
  - **Refactoring / Tech Debt**: Safety checks, incremental approach
  - Domain-specific optimization for common workflows
  - **Impact**: 40% improvement in first-time success rate (estimated)
  - **Effort**: M (3-5 days) × 4 templates = 3-4 weeks

- [ ] **EP-008**: Confirmation for destructive git operations [from BP guide v2.2 §8.3]
  - Granular control beyond current `--dangerous` mode
  - Specific prompts for force-push, hard reset, clean, branch deletion
  - Integration with GitManager
  - **Impact**: Prevents accidental data loss
  - **Effort**: S (1-2 days)

- [ ] **EP-009**: Security audit trail [from BP guide v2.2 §10.6]
  - Dedicated security log (separate from application logs)
  - Log: tool decisions, injection attempts, sanitization, permission changes
  - Immutable, retained indefinitely
  - **Impact**: Complete audit trail for security events
  - **Effort**: S (1-2 days)

**Expected Outcomes**:
- ✅ Obra safe for wider distribution (security addressed)
- ✅ 30-40% better prompt quality (domain-specific templates)
- ✅ Machine-readable plans enable advanced automation
- ✅ Standardized outputs easier to parse/validate

**Target**: 10 weeks (March 2026 if started immediately)

---

### v1.6.0 - Enforcement & Observability **[Target: May 2026]**

**Theme**: Automation + production readiness

#### P1-HIGH Enforcement Automation (2-3 weeks)

- [ ] **EP-010**: Pre-commit hooks [from BP guide v2.2 §16.1]
  - Automated validation before git commits
  - Checks: linting, unit tests, security scan, secret detection
  - Plan manifest schema validation (if exists)
  - **Impact**: Prevents broken code from being committed
  - **Effort**: S (1-2 days)

- [ ] **EP-011**: CI/CD validation pipeline [from BP guide v2.2 §5.3]
  - GitHub Actions workflow for PRs
  - Stages: lint, type check, tests, security scan, plan validation, ADR format check
  - **Impact**: Automated quality gates, <5 min pipeline
  - **Effort**: M (3-5 days)

- [ ] **EP-014**: Automated security scanning [from BP guide v2.2 §9.5]
  - Python: bandit (SAST), safety/pip-audit (dependencies)
  - Git: gitleaks/detect-secrets (secrets in code)
  - Thresholds: CRITICAL fails build, HIGH warns
  - **Impact**: Zero high/critical vulnerabilities in production
  - **Effort**: S (1-2 days)

#### P1-HIGH Observability & Security (2-3 weeks)

- [ ] **EP-012**: Privacy-preserving logging [from BP guide v2.2 §10.5]
  - Integrate OutputSanitizer with all logging systems
  - Redact PII/secrets before writing logs
  - Configurable redaction rules
  - **Impact**: Safe to share/analyze logs
  - **Effort**: M (3-5 days)

- [ ] **EP-013**: Secrets management enhancement [from BP guide v2.2 §9.2]
  - Support: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
  - Encrypted local secrets file (for solo devs)
  - Multi-backend support via config
  - **Impact**: Secrets never in git, easy rotation
  - **Effort**: S (1-2 days)

- [ ] **EP-015**: Security-first design principles [from BP guide v2.2 §9.1]
  - Document principles: Least Privilege, Defense in Depth, Fail Secure, Explicit Trust, Audit Everything
  - Create `docs/architecture/SECURITY_PRINCIPLES.md`
  - Security checklist for new features
  - **Impact**: Formalized security culture
  - **Effort**: S (1-2 days)

#### P1-HIGH Polish (1 week)

- [ ] **EP-016**: User story format in tasks [from BP guide v2.2 §2.3]
  - Add `user_story`, `acceptance_criteria`, `design_intent` fields to Task model
  - Database migration (backward-compatible)
  - Parse from task descriptions
  - **Impact**: Better Claude context, improved understanding
  - **Effort**: S (1-2 days)

- [ ] **EP-017**: Planning/execution templates [from BP guide v2.2 §12]
  - Separate templates for planning vs execution phases
  - Planning: architecture, breakdown, dependencies → plan_manifest + ADRs
  - Execution: code gen, tests, validation → code + tests + docs
  - **Impact**: Clear phase separation, reduced confusion
  - **Effort**: M (3-5 days)

- [ ] Quick reference card [from BP guide v2.2 §16.2]
  - One-page cheat sheet for users
  - Common commands, workflows, troubleshooting
  - **Effort**: XS (<1 day)

**Expected Outcomes**:
- ✅ Fully automated quality gates (no manual checks)
- ✅ Safe for logs to be shared/analyzed (privacy)
- ✅ Better developer experience (quick reference)
- ✅ Production-ready observability

**Target**: 4 weeks (May 2026)

---

### v1.7.0 - Advanced Orchestration **[Target: Q3 2026]**

**Theme**: Multi-agent maturity + optimization

#### P2-MEDIUM Multi-Agent Enhancement (6-8 weeks)

- [ ] ParallelAgentCoordinator maturation [from BP guide v2.2 §6.2]
  - Stable parallel specialist pattern
  - Improved merge conflict resolution
  - Resource allocation management
  - **Effort**: M (3-5 days)

- [ ] Standard message format for agents [from BP guide v2.2 §6.5]
  - JSON schema for inter-agent communication
  - Correlation IDs, message types, priority levels
  - **Effort**: M (3-5 days)

- [ ] Hierarchical delegation (multi-agent epics) [from BP guide v2.2 §6.4]
  - Epic-level agent coordination
  - Architect agent delegates to specialist agents
  - **Effort**: M (3-5 days)

- [ ] Correlation IDs formalized [from BP guide v2.2 §6.6]
  - Link related logs/metrics across agents
  - Distributed tracing lite
  - **Effort**: S (1-2 days)

#### P2-MEDIUM Context Optimization (6-8 weeks)

- [ ] Summarization for completed phases [from BP guide v2.2 §4.2]
  - Compress finished work into ≤500 token summaries
  - Maintain context continuity with less overhead
  - **Effort**: M (3-5 days)

- [ ] Artifact registry (file→description) [from BP guide v2.2 §4.3]
  - Track files with concise descriptions instead of full contents
  - Reduce context window usage
  - **Effort**: M (3-5 days)

- [ ] Formalized checkpointing protocol [from BP guide v2.2 §4.8]
  - Checkpoint artifacts: snapshot, resume instructions, artifact registry
  - Automatic checkpointing at thresholds
  - **Effort**: M (3-5 days)

- [ ] Token budget allocation [from BP guide v2.2 §4.7]
  - Planning 15-20%, Implementation 50-60%, Validation 10-15%, Buffer 10-15%
  - Per-task budgets with alerts
  - **Effort**: S (1-2 days)

#### P2-MEDIUM Decision Trees (3-4 weeks)

- [ ] Explicit decision trees for validation failures [from BP guide v2.2 §11.3]
  - Formalize QualityController decision logic
  - Visual decision tree documentation
  - **Effort**: S (1-2 days)

- [ ] Rollback decision tree formalized [from BP guide v2.2 §11.5]
  - When to rollback vs retry vs escalate
  - GitManager integration
  - **Effort**: M (3-5 days)

- [ ] Circuit breaker pattern [from BP guide v2.2 §11.8]
  - Prevent cascading failures (e.g., rate limiting)
  - Auto-recovery after cooldown
  - **Effort**: S (1-2 days)

**Expected Outcomes**:
- ✅ Complex multi-agent workflows (parallel, hierarchical)
- ✅ Better context efficiency (larger projects)
- ✅ Explicit decision-making (easier to debug)

**Target**: 6-8 weeks

---

### v2.0.0 - Enterprise & Scale **[Target: TBD based on user demand]**

**Theme**: Enterprise features IF market demand proven

#### Potential Features (Deferred)

**Enterprise Compliance** (XL effort):
- GDPR compliance framework
- HIPAA compliance framework
- SOC2 compliance framework
- Data classification handling
- Retention policies

**Advanced RAG Integration** (XL effort):
- Vector store integration
- Semantic chunking
- Document validation
- RAG-specific security controls
- (Only if Obra adds RAG capability)

**Web UI Dashboard** (XL effort):
- Real-time project dashboard
- Visual task hierarchy
- Performance metrics charts
- Agent activity monitoring
- Integrated code editor

**Distributed Orchestration** (XL effort):
- Multi-machine coordination
- Cloud deployment support
- Horizontal scaling
- Load balancing

**Decision Criteria for v2.0 Features**:
- ≥50 active enterprise users requesting feature
- Clear revenue opportunity
- Doesn't compromise core simplicity
- Market validation via beta testing

---

## Quick Wins (High ROI, Low Effort)

These items can be implemented in <2 days each with significant impact:

### Security Quick Wins (v1.5.0)
1. ✅ **Input sanitization basic patterns** (S effort, P0)
   - Regex-based injection detection
   - Immediate security improvement
   - **ROI**: Critical security fix

2. ✅ **Tool output sanitization** (S effort, P0)
   - Redact common PII/secret patterns
   - **ROI**: Prevents data leaks

3. ✅ **Confirmation for destructive git ops** (S effort, P1)
   - Prevent accidental force-push, hard reset
   - **ROI**: Zero data loss from accidents

### Prompt Quality Quick Wins (v1.5.0)
4. ✅ **Bug fix template** (S effort, P1)
   - High-frequency use case
   - Clear structure
   - **ROI**: 40% better bug fix quality (estimated)

5. ✅ **Refactoring template** (S effort, P1)
   - Common workflow
   - Well-defined pattern
   - **ROI**: Safer refactoring, fewer regressions

6. ✅ **Approval gate timestamps** (XS effort, P2)
   - Add to interactive mode
   - **ROI**: Better auditability

### Automation Quick Wins (v1.6.0)
7. ✅ **Pre-commit hook for linting** (S effort, P1)
   - Prevent broken code from reaching Claude
   - **ROI**: Zero lint errors in commits

8. ✅ **Quick reference card** (XS effort, P2)
   - Single-page cheat sheet
   - **ROI**: Better UX, lower learning curve

### Observability Quick Wins (v1.6.0)
9. ✅ **Structured logging format** (S effort, P2)
   - Standardize on JSON
   - **ROI**: Easier parsing, better tooling

10. ✅ **Correlation ID formalization** (S effort, P2)
    - Link related logs/metrics
    - **ROI**: Easier debugging

**Total Quick Wins Effort**: 8-10 days
**Expected Impact**: Immediate security + UX improvements, foundation for v1.5.0/v1.6.0

---

## Archived / Original Ideas

The following ideas from original `design_future.md` are preserved but deprioritized:

### Obra Terminal / UI (v2.0+)
- Project dashboard (visual)
- Real-time collaboration
- Integrated code editor
- Customizable themes

### Obra Setup / Netcode (v2.0+)
- Remove hard-coded IPs (partially done in v1.4.0)
- Automatic network detection
- Dynamic IP assignment

### Recovery (Partially Done in v1.2-1.3)
- ✅ Auto-save project state (StateManager)
- ✅ Restart from last state (SessionManager)
- ⚠️ Crash cause analysis (basic logging, needs enhancement)
- ✅ Resume interrupted tasks (interactive checkpoints)

### Bugfixing / Error Recovery (Partially Done in v1.3)
- ✅ Retry with exponential backoff
- ⚠️ Escalation system (implicit in DecisionEngine, needs formalization)
- ⚠️ Prompt modification on failure (basic retry, could enhance)

### Performance / Efficiency (v1.7+)
- Task delegation logic (rAI vs VD) - defer to v1.7
- Multiple context windows (ParallelAgentCoordinator foundation exists)
- Local hardware specs detection - defer to v2.0

### Agenting (Partially Done in v1.3)
- ✅ Agent specialization (via plugins)
- ⚠️ Parallel agent deployment (ParallelAgentCoordinator exists, needs maturity)
- ⚠️ Agent lifecycle management (basic, needs enhancement)

### Testing (Done in v1.1)
- ✅ Automated testing framework (91% coverage)
- ✅ Unit, integration, E2E tests
- ✅ LLM-optimized format (StructuredPromptBuilder)

### Logging (Partially Done, Enhancement in v1.6.0)
- ✅ Structured logging (Python logging module)
- ⚠️ LLM-consumable format (needs standardization - EP-012)
- ⚠️ Separated logs (project/agent/orchestrator) - partial

### Statusing and Project Management (Done in v1.3)
- ✅ LLM-optimized planning (StructuredPromptBuilder)
- ✅ Break into parallel tasks (DependencyResolver, ParallelAgentCoordinator)
- ✅ Include testing in dev process (validation pipeline)

---

## Success Metrics

### Security Metrics (post v1.5.0)
- Zero successful prompt injections in testing
- Zero PII leaks in logs
- 100% of destructive operations confirmed
- Complete audit trail for all security events

### Quality Metrics (post v1.5.0)
- 30-40% improvement in first-time success rate for templated tasks
- 50% reduction in prompt confusion/misunderstanding
- Valid plan_manifest.json generated for 100% of epics

### Automation Metrics (post v1.6.0)
- Zero manual lint/test runs (automated via hooks)
- 100% PR validation via CI/CD
- <5 min CI/CD pipeline duration

### Adoption Metrics
- ≥80% of tasks use specialized templates (vs generic)
- ≥95% of users keep security features enabled
- ≥90% user satisfaction with new UX

### Business Metrics (long-term)
- Monthly active users (MAU)
- Task completion rate
- Average tasks per user per month
- User retention (30-day, 90-day)
- NPS (Net Promoter Score)

---

## Risk Management

### Technical Risks
- **Risk**: Plan manifest schema too rigid
  - **Mitigation**: Iterate based on user feedback, start minimal
- **Risk**: Security features break workflows
  - **Mitigation**: All features configurable, can be disabled
- **Risk**: Performance degradation
  - **Mitigation**: Benchmark each feature, optimize hot paths

### Adoption Risks
- **Risk**: Users disable security features
  - **Mitigation**: Clear risk docs, graduated security levels
- **Risk**: Templates don't match workflows
  - **Mitigation**: Beta test, make customizable

### Timeline Risks
- **Risk**: Estimates too optimistic
  - **Mitigation**: 50% buffer, ruthless prioritization
- **Risk**: Scope creep
  - **Mitigation**: Freeze requirements per phase

---

## Decision Framework

**When to add a feature**:
1. Aligns with solo/small team focus
2. Evidence of user need (requests, surveys, usage data)
3. Doesn't compromise simplicity
4. Clear ROI (time saved, quality improved, errors prevented)
5. Fits into product narrative

**When to defer a feature**:
1. Enterprise-only (wait for market validation)
2. Premature optimization
3. Technology not mature enough
4. Unclear ROI
5. Out of scope for current vision

**When to reject a feature**:
1. Over-complicates core workflows
2. Maintenance burden too high
3. Security/privacy concerns
4. Doesn't align with mission

---

**Roadmap Version**: 2.0
**Last Updated**: 2025-11-11
**Next Review**: After v1.5.0 release (March 2026)
**Maintained By**: Obra development team

**References**:
- Best Practices Assessment: `docs/design/obra-best-practices-assessment.md`
- Enhancement Proposals: `docs/design/enhancements/`
- LLM Dev Prompt Guide v2.2: `docs/research/llm-dev-prompt-guide-v2_2.md`
