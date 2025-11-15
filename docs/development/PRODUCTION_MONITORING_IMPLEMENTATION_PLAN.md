# Production Monitoring Implementation Plan

**Version:** 1.0
**Date:** November 15, 2025
**Status:** Planning
**Estimated Effort:** 8-10 hours
**Target Version:** v1.8.0

---

## Executive Summary

Implement structured production logging for Obra interactive REPL to enable:
- Real-time monitoring of NL command quality
- Performance bottleneck identification
- Production issue detection and debugging
- Data-driven prompt engineering improvements

**Key Deliverable:** JSON Lines logging capturing I/O boundaries + critical metadata while excluding verbose in-progress messages.

---

## Background

### Current State
- Interactive REPL has extensive debug logging (all stages, in-progress messages)
- No structured production logging
- No session tracking across multi-turn conversations
- No performance metrics collection
- No NL pipeline quality tracking

### Motivation
From workflow testing (v1.7.3):
- Found 2 critical bugs through real usage
- Phase 4 NL testing: 95% acceptance, 73% variation pass rate
- 27% of edge cases may fail in production
- Need visibility into real user NL command patterns

### Success Criteria
1. ✅ All I/O boundaries logged (user input → result)
2. ✅ NL pipeline quality metrics captured (confidence, validation)
3. ✅ Performance metrics tracked (latency per stage)
4. ✅ Session continuity across multi-turn conversations
5. ✅ Privacy-preserving (PII/secret redaction optional)
6. ✅ Minimal performance overhead (<5% latency increase)
7. ✅ Log volume <100MB/day for typical usage (10-20 sessions)

---

## Architecture

### Log Event Types

```jsonl
# 1. User Input
{"type": "user_input", "ts": "ISO8601", "session": "uuid",
 "input": "delete all projects"}

# 2. NL Processing Result (NEW - critical addition)
{"type": "nl_result", "ts": "ISO8601", "session": "uuid",
 "intent": "COMMAND", "confidence": 0.91,
 "operation": "DELETE", "entity": "project", "identifier": "__ALL__",
 "validation": "passed", "duration_ms": 1234,
 "stages": {"intent": 0.94, "operation": 1.0, "entity": 0.90, "params": 0.80}}

# 3. Orchestrator → Implementer Prompt (optional, disabled by default)
{"type": "orch_prompt", "ts": "ISO8601", "session": "uuid", "task_id": 7,
 "target": "claude-code", "prompt_length": 1500, "context_tokens": 5000}

# 4. Implementer Response (optional, disabled by default)
{"type": "impl_response", "ts": "ISO8601", "session": "uuid", "task_id": 7,
 "success": true, "duration_ms": 8500, "output_length": 2300}

# 5. Execution Result
{"type": "execution_result", "ts": "ISO8601", "session": "uuid",
 "success": true, "message": "Deleted 15 projects",
 "entities_affected": {"projects": 15}, "total_duration_ms": 9800}

# 6. Error (when applicable)
{"type": "error", "ts": "ISO8601", "session": "uuid",
 "stage": "validation", "error_type": "ValidationException",
 "error": "Project ID must be positive integer", "recoverable": true}
```

### Component Design

```
┌─────────────────────────────────────────────────────────┐
│                   Interactive REPL                       │
│  ┌────────────────────────────────────────────────┐    │
│  │ User Input → ProductionLogger.log_user_input() │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                                │
│  ┌────────────────────────────────────────────────┐    │
│  │ NL Processing → ProductionLogger.log_nl_result()│    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                                │
│  ┌────────────────────────────────────────────────┐    │
│  │ Execution → ProductionLogger.log_exec_result() │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                                │
│                  Display to User                         │
└─────────────────────────────────────────────────────────┘
                            ↓
              ┌─────────────────────────────┐
              │  production.jsonl (rotating)│
              │  - 100MB max per file       │
              │  - Keep 10 files (1GB)      │
              │  - Auto-rotate              │
              └─────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (3-4 hours)

**Story 1.1: ProductionLogger Class**
- Create `src/monitoring/production_logger.py`
- Implement JSON Lines logging
- Add rotating file handler (100MB files, keep 10)
- Session ID generation (UUID4)
- Timestamp formatting (ISO8601 with UTC)
- Thread-safe logging

**Story 1.2: Event Logging Methods**
- `log_user_input(session_id, input_text)`
- `log_nl_result(session_id, parsed_intent, duration_ms)`
- `log_execution_result(session_id, result, duration_ms)`
- `log_error(session_id, stage, error)`
- Optional: `log_orch_prompt()`, `log_impl_response()`

**Story 1.3: Configuration**
- Add `monitoring` section to `config/config.yaml`
- Enable/disable toggle
- Log path configuration
- Privacy settings (redact_pii, redact_secrets)
- Rotation settings

**Deliverables:**
- ✅ `src/monitoring/__init__.py`
- ✅ `src/monitoring/production_logger.py` (200-250 lines)
- ✅ Configuration schema
- ✅ Unit tests (15-20 tests)

---

### Phase 2: Interactive REPL Integration (2-3 hours)

**Story 2.1: Initialize ProductionLogger**
- Add to `InteractiveMode.__init__()`
- Generate session ID on REPL start
- Conditionally enable based on config

**Story 2.2: Log User Input**
- Hook into natural language handler
- Log all user input (NL commands, slash commands)
- Track timestamp

**Story 2.3: Log NL Processing Results**
- Capture `ParsedIntent` after `nl_processor.process()`
- Extract confidence scores from all 4 stages
- Log validation pass/fail
- Track duration from input to parse completion

**Story 2.4: Log Execution Results**
- Hook after `orchestrator.execute_nl_command()`
- Capture success/failure, message, entities affected
- Track total execution duration

**Story 2.5: Log Errors**
- Wrap try/except blocks
- Log stage where error occurred
- Include error type and message
- Track recoverable vs non-recoverable

**Deliverables:**
- ✅ Modified `src/interactive.py` (~50 lines added)
- ✅ Integration tests (8-10 tests)

---

### Phase 3: Privacy & Security (1-2 hours)

**Story 3.1: PII Redaction**
- Regex patterns for emails, IPs, phone numbers
- Optional redaction in `log_user_input()`
- Configuration flag: `redact_pii`

**Story 3.2: Secret Redaction**
- Detect common secret patterns (tokens, API keys)
- Redact from user input and error messages
- Configuration flag: `redact_secrets`

**Story 3.3: Configurable Logging Levels**
- `log_implementer_prompts: false` (default)
- `log_implementer_responses: false` (default)
- Allow enabling for deep debugging

**Deliverables:**
- ✅ `src/monitoring/redaction.py` (utility functions)
- ✅ Privacy tests (6-8 tests)

---

### Phase 4: Analysis Tools (1-2 hours)

**Story 4.1: Log Analysis Scripts**
- `scripts/monitoring/analyze_logs.py`
- Success rate by operation type
- Average confidence by intent
- Latency percentiles (P50, P95, P99)
- Error rate by stage

**Story 4.2: Real-time Monitoring**
- `scripts/monitoring/tail_logs.sh`
- Colorized output for different event types
- Filter by session ID
- Alert on errors

**Story 4.3: Dashboard Generator**
- `scripts/monitoring/generate_dashboard.py`
- HTML dashboard with charts
- Last 24h/7d/30d views
- Top failures, slowest operations

**Deliverables:**
- ✅ 3 analysis scripts
- ✅ Example queries in README
- ✅ Dashboard template

---

### Phase 5: Documentation & Testing (1-2 hours)

**Story 5.1: User Documentation**
- `docs/guides/PRODUCTION_MONITORING_GUIDE.md`
- Configuration examples
- How to analyze logs
- Troubleshooting common issues

**Story 5.2: Developer Documentation**
- Update `CLAUDE.md` with monitoring section
- API reference for ProductionLogger
- Integration guide for new features

**Story 5.3: Integration Testing**
- End-to-end test: REPL session → log verification
- Test all event types logged correctly
- Test log rotation
- Test privacy redaction

**Deliverables:**
- ✅ User guide
- ✅ Developer docs
- ✅ E2E tests (5-8 tests)

---

## Technical Specifications

### File Structure

```
src/monitoring/
├── __init__.py
├── production_logger.py      # Core logger class
└── redaction.py               # Privacy utilities

scripts/monitoring/
├── analyze_logs.py            # Log analysis
├── tail_logs.sh               # Real-time monitoring
└── generate_dashboard.py     # Dashboard generator

docs/guides/
└── PRODUCTION_MONITORING_GUIDE.md

tests/monitoring/
├── test_production_logger.py
├── test_redaction.py
└── test_integration.py
```

### Configuration Schema

```yaml
monitoring:
  production_logging:
    # Master enable/disable
    enabled: true

    # Log file location
    path: "~/obra-runtime/logs/production.jsonl"

    # What to log
    events:
      user_input: true
      nl_results: true
      execution_results: true
      errors: true
      orchestrator_prompts: false    # Disabled by default
      implementer_responses: false   # Disabled by default

    # Privacy
    privacy:
      redact_pii: true               # Email, IP, phone
      redact_secrets: true           # API keys, tokens
      redact_patterns: []            # Custom regex patterns

    # Rotation
    rotation:
      max_file_size_mb: 100
      max_files: 10                  # 1GB total

    # Performance
    async_logging: false             # Sync by default (simpler)
    buffer_size: 1024                # Flush every 1KB
```

### API Design

```python
class ProductionLogger:
    """Structured production logging for monitoring."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize logger from config."""

    def log_user_input(
        self,
        session_id: str,
        input_text: str,
        redact: bool = True
    ) -> None:
        """Log user input event."""

    def log_nl_result(
        self,
        session_id: str,
        parsed_intent: ParsedIntent,
        duration_ms: int
    ) -> None:
        """Log NL processing result with quality metrics."""

    def log_execution_result(
        self,
        session_id: str,
        result: Dict[str, Any],
        duration_ms: int
    ) -> None:
        """Log execution result."""

    def log_error(
        self,
        session_id: str,
        stage: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error with context."""

    def close(self) -> None:
        """Flush and close logger."""
```

---

## Testing Strategy

### Unit Tests (30+ tests)

**ProductionLogger Tests:**
- ✅ Log file creation and rotation
- ✅ JSON format validation
- ✅ Timestamp format (ISO8601)
- ✅ Session ID generation (UUID4)
- ✅ Thread-safety (concurrent writes)
- ✅ Event serialization

**Redaction Tests:**
- ✅ Email redaction
- ✅ IP address redaction
- ✅ API key/token redaction
- ✅ Custom pattern redaction
- ✅ Preserve non-sensitive data

### Integration Tests (10+ tests)

**REPL Integration:**
- ✅ User input logged correctly
- ✅ NL results logged with all metadata
- ✅ Execution results logged
- ✅ Errors logged with stage info
- ✅ Session ID consistent across events
- ✅ Timestamps in order

**End-to-End:**
- ✅ Full REPL session → verify all events logged
- ✅ Multi-turn conversation → session tracking
- ✅ Error scenario → error event logged
- ✅ Log rotation triggered correctly

### Performance Tests

- ✅ Logging overhead <5% of total latency
- ✅ No blocking on file I/O
- ✅ Memory usage <10MB for 1000 events

---

## Rollout Plan

### Phase 1: Development (Week 1)
- Implement core infrastructure
- Unit tests passing
- Code review

### Phase 2: Integration (Week 1)
- Integrate with interactive.py
- Integration tests passing
- Manual testing

### Phase 3: Beta Testing (Week 2)
- Deploy with `enabled: false` by default
- Enable for 2-3 beta users
- Monitor for issues

### Phase 4: Production (Week 2)
- Enable by default
- Monitor log volume
- Fine-tune rotation settings

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Log volume too high | Disk space | Medium | Conservative rotation (100MB, 10 files) |
| Performance overhead | UX degradation | Low | Async logging optional, tested <5% |
| Privacy leak | Compliance | Medium | PII/secret redaction by default |
| Log parsing breaks | Monitoring fails | Low | Strict JSON schema validation |

---

## Success Metrics

### Quantitative
- ✅ All 6 event types logged correctly
- ✅ Test coverage ≥90% for monitoring module
- ✅ Performance overhead <5%
- ✅ Log rotation working (verified with 200MB test data)

### Qualitative
- ✅ Can answer: "What's the success rate for DELETE operations?"
- ✅ Can answer: "What's P95 latency for NL processing?"
- ✅ Can answer: "What are the top 5 failure modes?"
- ✅ Can debug: "Why did this user's command fail?"

---

## Future Enhancements

### Phase 6 (Future)
- **Real-time Alerting:** Webhook to Slack/Discord on errors
- **Metrics Export:** Prometheus/Grafana integration
- **Log Shipping:** Send to ELK/Splunk for centralized monitoring
- **Anomaly Detection:** ML-based detection of unusual patterns
- **A/B Testing Framework:** Track experiments in logs

---

## References

- **Workflow Testing:** v1.7.3 (found 2 bugs via real usage)
- **Phase 4 Results:** 95% acceptance, 73% variation pass rate
- **ADR-017:** Unified Execution Architecture
- **Related:** `docs/testing/WORKFLOW_BUG_LOG.md`

---

## Appendix A: Example Log Analysis Queries

```bash
# Success rate by operation
jq -s 'group_by(.operation) | map({
  operation: .[0].operation,
  total: length,
  success: (map(select(.success)) | length),
  rate: (map(select(.success)) | length) / length
})' production.jsonl

# Average confidence by intent
jq -s 'group_by(.intent) | map({
  intent: .[0].intent,
  avg_confidence: (map(.confidence) | add / length),
  count: length
})' production.jsonl

# P95 latency
jq -s 'map(.duration_ms) | sort | .[length * 0.95 | floor]' production.jsonl

# Top errors
jq -s 'map(select(.type == "error")) |
  group_by(.error_type) |
  map({error: .[0].error_type, count: length}) |
  sort_by(.count) | reverse | .[0:10]' production.jsonl
```

---

## Appendix B: Configuration Examples

### Minimal (Production)
```yaml
monitoring:
  production_logging:
    enabled: true
    path: "~/obra-runtime/logs/production.jsonl"
```

### Full Monitoring (Debug)
```yaml
monitoring:
  production_logging:
    enabled: true
    path: "~/obra-runtime/logs/production.jsonl"
    events:
      user_input: true
      nl_results: true
      execution_results: true
      errors: true
      orchestrator_prompts: true   # Enabled for debugging
      implementer_responses: true  # Enabled for debugging
    privacy:
      redact_pii: false  # Disabled for debugging
      redact_secrets: true
```

### Privacy-Focused
```yaml
monitoring:
  production_logging:
    enabled: true
    path: "~/obra-runtime/logs/production.jsonl"
    privacy:
      redact_pii: true
      redact_secrets: true
      redact_patterns:
        - "\\b\\d{3}-\\d{2}-\\d{4}\\b"  # SSN
        - "\\b\\d{16}\\b"                 # Credit card
```

---

**Document Version:** 1.0
**Last Updated:** November 15, 2025
**Next Review:** After Phase 5 completion
