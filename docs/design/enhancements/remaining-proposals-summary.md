# Remaining Enhancement Proposals Summary (EP-004 through EP-017)

**Note**: EP-001 through EP-003 have detailed specifications in `v1.5-v1.6-enhancement-proposals.md`.
This document provides executive summaries for the remaining 14 proposals.

---

## EP-004: Tool Output Sanitization

**Priority**: 🔴 P0-CRITICAL | **Effort**: S (1-2 days)

**Summary**: Sanitize Claude Code output to redact PII, secrets, and sensitive data before logging or displaying to users.

**Key Components**:
- PII detection patterns (emails, SSNs, phone numbers, addresses)
- Secret detection (API keys, passwords, tokens, AWS keys)
- Configurable redaction rules
- Integration with logging system

**Implementation**:
```python
# src/security/output_sanitizer.py
class OutputSanitizer:
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'api_key': r'(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})',
        'aws_key': r'AKIA[0-9A-Z]{16}',
        'private_key': r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
    }
```

**Success Criteria**: Zero PII/secrets in logs, <0.1% false positives

---

## EP-005: Plan Manifest Schema Implementation

**Priority**: 🟠 P1-HIGH | **Effort**: L (1-2 weeks)

**Summary**: Implement plan_manifest.json schema from guide Section 3 for machine-readable plans.

**Key Components**:
- JSON schema definition matching guide v2.2
- Plan generator from Epic/Story/Task models
- Schema validator
- Plan versioning and state tracking

**Schema Structure**:
```json
{
  "meta": {"epic_id", "created_at", "prompt_version", "approved_by"},
  "objective": {"summary", "user_stories", "success_criteria"},
  "constraints": {"max_tokens_per_phase", "test_coverage_min_pct", "security"},
  "dependencies": {"existing_packages", "new_packages", "tools_and_resources"},
  "plan": {"phases": [{"stories": [{"tasks": [...]}]}], "decision_records": [...]},
  "state": {"current_phase", "completed_tasks", "validation_results"}
}
```

**Success Criteria**: All epics generate valid plan_manifest.json, schema validation passes

---

## EP-006: Canonical 11-Section Prompt Structure

**Priority**: 🟠 P1-HIGH | **Effort**: M (3-5 days)

**Summary**: Align StructuredPromptBuilder with guide's 11-section canonical structure.

**11 Sections**:
1. Agent Identity & Permissions
2. Objective & Design Intent
3. Context & Constraints
4. Reasoning Requirements
5. Deliverables & Formats
6. Acceptance Criteria
7. Planning Rules
8. Execution Gates
9. Error Handling & Recovery
10. Observability Hooks
11. Security Controls

**Implementation**: Refactor StructuredPromptBuilder to generate all 11 sections consistently.

**Success Criteria**: All prompts follow canonical structure, improved Claude response quality

---

## EP-007: Specialized Task Templates

**Priority**: 🟠 P1-HIGH | **Effort**: M (3-5 days) per template

**Summary**: Create domain-specific prompt templates for common task types.

**Templates to Implement (v1.5.0)**:
1. **Frontend UI Feature** - React/Vue components, accessibility, responsive design
2. **API Endpoint Development** - REST/GraphQL, validation, error handling, docs
3. **Bug Fix** - Reproduction, root cause analysis, fix, regression tests
4. **Refactoring / Tech Debt** - Safety checks, test preservation, incremental approach

**Templates to Defer (v1.6.0+)**:
5. Data Pipeline / ETL
6. Infrastructure as Code (IaC)

**Template Structure**:
```python
class TaskTemplate:
    name: str
    description: str
    prompt_sections: dict  # Customized sections 1-11
    acceptance_criteria: list
    common_pitfalls: list
    examples: list
```

**Success Criteria**: 40% improvement in first-time success rate for templated task types

---

## EP-008: Confirmation for Destructive Operations

**Priority**: 🟠 P1-HIGH | **Effort**: S (1-2 days)

**Summary**: Granular confirmation for destructive git operations (currently --dangerous mode is all-or-nothing).

**Destructive Operations**:
- `git reset --hard`
- `git push --force`
- `git clean -fd`
- `git branch -D`
- `rm -rf` commands
- Database migrations with DROP

**Implementation**: Extend ToolPolicy (EP-003) with git-specific rules, integrate with GitManager.

**Success Criteria**: Zero accidental data loss, clear user prompts for dangerous ops

---

## EP-009: Security Audit Trail

**Priority**: 🟠 P1-HIGH | **Effort**: S (1-2 days)

**Summary**: Dedicated security audit log separate from general application logs.

**What to Log**:
- Tool execution decisions (allowed/denied/confirmed)
- Prompt injection attempts (severity, patterns matched)
- Sanitization actions
- Permission changes
- Failed authentication (if multi-user added)

**Log Format**:
```json
{
  "timestamp": "2025-11-11T14:30:12Z",
  "event_type": "tool_execution",
  "tool_name": "Bash",
  "decision": "confirmed",
  "user_id": "user_hash",
  "session_id": "sess_12345",
  "details": {"command": "git push", "risk_level": "medium"}
}
```

**Storage**: Separate file `security_audit.jsonl`, immutable, retained indefinitely.

**Success Criteria**: Complete audit trail for all security events, tamper-evident

---

## EP-010: Pre-Commit Hooks

**Priority**: 🟠 P1-HIGH | **Effort**: S (1-2 days)

**Summary**: Automated validation before git commits.

**Checks**:
- Linting (pylint, mypy)
- Unit tests (pytest)
- Security scan (bandit for Python)
- No hardcoded secrets (detect-secrets)
- Plan manifest schema validation (if exists)

**Implementation**:
```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: obra-validation
        name: Obra validation suite
        entry: python -m src.validation.pre_commit_hook
        language: system
        pass_filenames: false
```

**Success Criteria**: Prevents broken code from being committed, <5s execution time

---

## EP-011: CI/CD Validation Pipeline

**Priority**: 🟠 P1-HIGH | **Effort**: M (3-5 days)

**Summary**: GitHub Actions workflow for automated validation on PRs.

**Pipeline Stages**:
1. Lint & Type Check
2. Unit Tests (with coverage report)
3. Integration Tests
4. Security Scanning
5. Plan Manifest Validation
6. Decision Record Format Check

**Workflow**:
```yaml
# .github/workflows/validation.yml
name: Obra Validation Pipeline
on: [pull_request, push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Run validation
        run: ./scripts/ci_validation.sh
```

**Success Criteria**: All PRs validated automatically, <5 min pipeline duration

---

## EP-012: Privacy-Preserving Logging

**Priority**: 🟠 P1-HIGH | **Effort**: M (3-5 days)

**Summary**: Integrate OutputSanitizer (EP-004) with all logging systems.

**Implementation**:
```python
# src/utils/privacy_logger.py
class PrivacyLogger:
    def __init__(self, base_logger, sanitizer):
        self.base_logger = base_logger
        self.sanitizer = sanitizer

    def info(self, message, **kwargs):
        sanitized = self.sanitizer.sanitize(message)
        self.base_logger.info(sanitized, **kwargs)
```

**Redaction Rules**:
- PII: `[EMAIL]`, `[PHONE]`, `[SSN]`
- Secrets: `[API_KEY]`, `[PASSWORD]`, `[TOKEN]`
- Paths: Optionally redact user home directories

**Success Criteria**: Zero PII in logs, logs still useful for debugging

---

## EP-013: Secrets Management Enhancement

**Priority**: 🟠 P1-HIGH | **Effort**: S (1-2 days)

**Summary**: Formalize secrets management with vault integration.

**Current**: Environment variables only
**Enhanced**:
- Support for HashiCorp Vault
- AWS Secrets Manager integration
- Azure Key Vault integration
- Encrypted local secrets file (for solo devs)

**Configuration**:
```yaml
[secrets]
backend = "vault"  # or "aws_secrets", "azure_keyvault", "env", "encrypted_file"
vault_url = "https://vault.internal:8200"
vault_token_path = "~/.vault-token"
```

**Success Criteria**: Secrets never in git, easy rotation, multi-backend support

---

## EP-014: Automated Security Scanning

**Priority**: 🟠 P1-HIGH | **Effort**: S (1-2 days)

**Summary**: Automated dependency and code vulnerability scanning.

**Tools**:
- Python: `bandit` (SAST), `safety` (dependency check), `pip-audit`
- Git: `gitleaks` or `detect-secrets` (pre-commit)
- Container: `trivy` (if Docker added)

**Integration**: CI/CD pipeline + pre-commit hooks

**Thresholds**:
- CRITICAL vulnerabilities: Fail build
- HIGH vulnerabilities: Warn, require review
- MEDIUM/LOW: Log only

**Success Criteria**: Zero high/critical vulnerabilities in production

---

## EP-015: Security-First Design Principles

**Priority**: 🟠 P1-HIGH | **Effort**: S (1-2 days)

**Summary**: Document and enforce security principles across Obra.

**Principles**:
1. **Least Privilege**: Tools/agents have minimum necessary permissions
2. **Defense in Depth**: Multiple layers (detection, sanitization, policy, audit)
3. **Fail Secure**: Default to deny if uncertain
4. **Explicit Trust**: No implicit assumptions about input safety
5. **Audit Everything**: Complete trail for security decisions

**Documentation**: Create `docs/architecture/SECURITY_PRINCIPLES.md`

**Enforcement**: Security checklist for all new features, required ADR for security changes

**Success Criteria**: All developers trained, principles referenced in code reviews

---

## EP-016: User Story Format in Tasks

**Priority**: 🟠 P1-HIGH | **Effort**: S (1-2 days)

**Summary**: Add user story fields to Task model for better context.

**Current Task Model**:
```python
class Task:
    id, project_id, description, status, ...
```

**Enhanced Task Model**:
```python
class Task:
    # ... existing fields
    user_story: Optional[str]  # "As a [user], I want [capability], so that [benefit]"
    acceptance_criteria: List[str]  # Observable outcomes
    design_intent: Optional[str]  # Why we're doing this
```

**Migration**: Add optional fields, populate from task description parsing

**Success Criteria**: Stories improve prompt quality, better Claude understanding

---

## EP-017: Planning/Execution Templates

**Priority**: 🟠 P1-HIGH | **Effort**: M (3-5 days) for both

**Summary**: Separate templates for planning phase vs execution phase prompts.

**Planning Template** (Sections 1-7):
- Focus: Architecture decisions, task breakdown, dependency analysis
- Output: plan_manifest.json, ADRs, design docs
- Validation: Completeness, feasibility, resource estimation

**Execution Template** (Sections 8-11):
- Focus: Code generation, testing, quality gates
- Input: Approved plan_manifest.json
- Output: Code, tests, documentation
- Validation: Tests pass, lint clean, security scanned

**Implementation**: Extend StructuredPromptBuilder with `build_planning_prompt()` and `build_execution_prompt()` methods.

**Success Criteria**: Clear phase separation, reduced prompt confusion, better outputs

---

## Cross-Cutting Enhancements

### Testing Requirements

All enhancements MUST include:
- Unit tests (≥90% coverage for new code)
- Integration tests (where applicable)
- Security tests (for security enhancements)
- Performance tests (if latency-sensitive)

### Documentation Requirements

All enhancements MUST include:
- Update CLAUDE.md if architecture changes
- Add/update ADR if design decision made
- User-facing docs in `docs/guides/`
- Code-level docstrings (Google style)
- Update CHANGELOG.md

### Migration Strategy

All database changes:
- Backward-compatible migrations
- Rollback scripts provided
- Test migration on copy of production data
- Document migration in ADR

### Configuration

All new features:
- Configurable via `config.yaml`
- Sane defaults (fail-secure for security features)
- Environment variable override support
- Documented in `docs/guides/CONFIGURATION_PROFILES_GUIDE.md`

---

## Implementation Order (Recommended)

### Phase 1: Critical Security (3 weeks)
1. EP-001: Prompt Injection Detection (M)
2. EP-002: Input Sanitization (S)
3. EP-003: Tool Execution Allowlisting (M)
4. EP-004: Tool Output Sanitization (S)

**Blockers Removed**: Obra safe for wider distribution

### Phase 2: Structured Outputs (4-5 weeks)
5. EP-005: Plan Manifest Schema (L)
6. EP-006: Canonical 11-Section Prompts (M)
7. EP-007: Specialized Templates (M × 4 templates)
8. EP-016: User Story Format (S)
9. EP-017: Planning/Execution Templates (M)

**Blockers Removed**: Industry-standard outputs, domain optimization

### Phase 3: Enforcement (v1.6.0 - 2 weeks)
10. EP-010: Pre-Commit Hooks (S)
11. EP-011: CI/CD Pipeline (M)
12. EP-014: Automated Security Scanning (S)

**Blockers Removed**: Manual quality checks

### Phase 4: Observability & Hardening (v1.6.0 - 2 weeks)
13. EP-009: Security Audit Trail (S)
14. EP-012: Privacy-Preserving Logging (M)
15. EP-013: Secrets Management (S)
16. EP-008: Confirmation for Destructive Ops (S)
17. EP-015: Security-First Principles (S)

**Blockers Removed**: Production-ready observability

---

## Total Effort Estimate

- **P0-CRITICAL (4 items)**: ~3 weeks
- **P1-HIGH v1.5.0 (9 items)**: ~7 weeks
- **P1-HIGH v1.6.0 (8 items)**: ~4 weeks

**Total**: 14 weeks (3.5 months) at 100% allocation
**Realistic** (50% allocation): 28 weeks (7 months)

**v1.5.0 Target**: 10 weeks → March 2026 (if started immediately)
**v1.6.0 Target**: 4 weeks after v1.5.0 → May 2026

---

## Risk Mitigation

### Technical Risks
- **Risk**: Plan manifest schema too rigid, doesn't fit real workflows
  - **Mitigation**: Start with minimal schema, iterate based on user feedback
- **Risk**: Security features break existing workflows
  - **Mitigation**: All security features configurable, can be disabled for testing
- **Risk**: Performance degradation from sanitization/validation
  - **Mitigation**: Benchmark each feature, optimize hot paths, add caching

### Adoption Risks
- **Risk**: Users disable security features because too restrictive
  - **Mitigation**: Clear documentation of risks, graduated security levels (strict/balanced/permissive)
- **Risk**: Templates don't match user workflows
  - **Mitigation**: Beta test with real users, make templates customizable

### Timeline Risks
- **Risk**: Estimates too optimistic
  - **Mitigation**: Add 50% buffer, prioritize P0 ruthlessly
- **Risk**: Scope creep during implementation
  - **Mitigation**: Freeze requirements for each phase, defer enhancements to next version

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

---

**Document Version**: 1.0
**Last Updated**: 2025-11-11
**Maintained By**: Obra development team
