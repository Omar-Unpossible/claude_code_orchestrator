# Production Monitoring Guide

**Version**: 1.8.1
**Last Updated**: November 15, 2025

---

## Overview

Obra includes built-in **production logging** for real-time observability and quality monitoring. The system captures I/O boundaries, quality metrics, and errors while automatically protecting privacy through PII and secret redaction.

**Key Features:**
- JSON Lines format for easy parsing and analysis
- Automatic privacy protection (PII/secret redaction)
- Session tracking for multi-turn conversations
- Configurable event filtering
- Automatic log rotation
- Thread-safe concurrent logging

---

## Quick Start

### Enable Production Logging

Production logging is **enabled by default** in v1.8.0. To verify or customize:

```yaml
# config/config.yaml
monitoring:
  production_logging:
    enabled: true  # Default: enabled
    path: "~/obra-runtime/logs/production.jsonl"
```

### View Logs

```bash
# View all logs (formatted with jq)
cat ~/obra-runtime/logs/production.jsonl | jq .

# View latest 10 events
tail -10 ~/obra-runtime/logs/production.jsonl | jq .

# Follow logs in real-time
tail -f ~/obra-runtime/logs/production.jsonl | jq .
```

---

## Event Types

### 1. User Input (`user_input`)

Captures all user commands and natural language input.

**Fields:**
- `type`: "user_input"
- `ts`: ISO 8601 timestamp
- `session`: Session UUID
- `input`: User's input text (PII/secrets redacted)

**Example:**
```json
{
  "type": "user_input",
  "ts": "2025-11-15T10:23:45.123456+00:00",
  "session": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "input": "delete all projects"
}
```

### 2. NL Processing Result (`nl_result`)

Records natural language parsing quality and performance.

**Fields:**
- `type`: "nl_result"
- `ts`: ISO 8601 timestamp
- `session`: Session UUID
- `intent`: Intent type (COMMAND, QUESTION)
- `confidence`: Confidence score (0.0-1.0)
- `operation`: Operation type (CREATE, DELETE, QUERY, UPDATE)
- `entity`: Entity type (project, epic, story, task)
- `identifier`: Entity identifier (ID, name, or __ALL__)
- `validation`: Validation status (passed, failed)
- `duration_ms`: Processing duration in milliseconds

**Example:**
```json
{
  "type": "nl_result",
  "ts": "2025-11-15T10:23:45.234567+00:00",
  "session": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "intent": "COMMAND",
  "confidence": 0.91,
  "operation": "DELETE",
  "entity": "project",
  "identifier": "__ALL__",
  "validation": "passed",
  "duration_ms": 1234
}
```

### 3. Execution Result (`execution_result`)

Tracks task execution outcomes and performance.

**Fields:**
- `type`: "execution_result"
- `ts`: ISO 8601 timestamp
- `session`: Session UUID
- `success`: Boolean success flag
- `message`: Result message
- `entities_affected`: Count of entities affected
- `total_duration_ms`: Total execution duration in milliseconds

**Example:**
```json
{
  "type": "execution_result",
  "ts": "2025-11-15T10:23:55.123456+00:00",
  "session": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "success": true,
  "message": "Deleted 15 projects",
  "entities_affected": {"projects": 15},
  "total_duration_ms": 9800
}
```

### CLI Command Logging (v1.8.1)

**New in v1.8.1**: Production logging now captures **all CLI commands**, not just natural language commands through the interactive REPL.

**Logged CLI Commands**:
- `obra task execute <id>` → user_input + execution_result
- `obra project create <name>` → user_input + execution_result
- `obra epic create <title>` → user_input + execution_result
- `obra story create <title>` → user_input + execution_result
- `obra task create <title>` → user_input + execution_result

**Example: CLI Task Execution**

**user_input event**:
```json
{
  "type": "user_input",
  "ts": "2025-11-16T00:49:34.811775+00:00",
  "session": "0f74fa64-387f-4031-8095-ad83d1632bd7",
  "input": "task execute 9 --max-iterations=10 --stream"
}
```

**execution_result event**:
```json
{
  "type": "execution_result",
  "ts": "2025-11-16T00:56:00.381248+00:00",
  "session": "0f74fa64-387f-4031-8095-ad83d1632bd7",
  "success": true,
  "message": "Task 9 completed",
  "entities_affected": {
    "task_id": 9,
    "status": "completed",
    "outcome": "partial",
    "quality_score": 0.75,
    "confidence": 0.938,
    "iterations": 3,
    "files_created": 6
  },
  "total_duration_ms": 385569
}
```

**Query Examples**:
```bash
# Find all CLI task executions
jq 'select(.type == "user_input" and (.input | contains("task execute")))' \
  ~/obra-runtime/logs/production.jsonl

# Get execution results with quality scores
jq 'select(.type == "execution_result" and .entities_affected.quality_score != null) |
    {task_id: .entities_affected.task_id, quality: .entities_affected.quality_score,
     outcome: .entities_affected.outcome, iterations: .entities_affected.iterations}' \
  ~/obra-runtime/logs/production.jsonl

# Find tasks with partial outcomes (v1.8.1 deliverable assessment)
jq 'select(.type == "execution_result" and .entities_affected.outcome == "partial")' \
  ~/obra-runtime/logs/production.jsonl
```

**Deliverable Outcomes (v1.8.1)**:

New task outcomes tracked in execution_result events:
- **success**: Completed within all limits
- **success_limits**: Completed but hit max_turns limit (deliverables detected)
- **partial**: Incomplete but created valuable deliverables
- **failed**: No deliverables or low quality
- **blocked**: Cannot proceed

---

### 4. Error (`error`)

Captures errors with stage context for debugging.

**Fields:**
- `type`: "error"
- `ts`: ISO 8601 timestamp
- `session`: Session UUID
- `stage`: Stage where error occurred (nl_processing, validation, execution)
- `error_type`: Exception type
- `error`: Error message
- `recoverable`: Whether error is recoverable (boolean)
- `context`: Additional context (optional)

**Example:**
```json
{
  "type": "error",
  "ts": "2025-11-15T10:24:01.123456+00:00",
  "session": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "stage": "validation",
  "error_type": "ValueError",
  "error": "Project ID must be positive",
  "recoverable": true,
  "context": {"task_id": 7}
}
```

### 5. Orchestrator Prompt (`orch_prompt`) - Optional

Logs prompts sent to implementer (disabled by default, verbose).

**Fields:**
- `type`: "orch_prompt"
- `ts`: ISO 8601 timestamp
- `session`: Session UUID
- `task_id`: Task ID
- `target`: Target implementer (e.g., "claude-code")
- `prompt_length`: Prompt length in characters
- `context_tokens`: Number of context tokens

### 6. Implementer Response (`impl_response`) - Optional

Logs implementer responses (disabled by default, verbose).

**Fields:**
- `type`: "impl_response"
- `ts`: ISO 8601 timestamp
- `session`: Session UUID
- `task_id`: Task ID
- `success`: Success flag
- `duration_ms`: Implementation duration
- `output_length`: Output length in characters

---

## Configuration

### Full Configuration Reference

```yaml
# config/config.yaml
monitoring:
  production_logging:
    # Master enable/disable
    enabled: true

    # Log file location
    path: "~/obra-runtime/logs/production.jsonl"

    # Event filtering
    events:
      user_input: true              # User commands/NL input
      nl_results: true              # NL parsing quality
      execution_results: true       # Task execution outcomes
      errors: true                  # Errors with context
      orchestrator_prompts: false   # Prompts to implementer (verbose)
      implementer_responses: false  # Implementer responses (verbose)

    # Privacy settings
    privacy:
      redact_pii: true              # Email, IP, phone, SSN
      redact_secrets: true          # API keys, tokens
      redact_patterns: []           # Custom regex patterns (future)

    # Log rotation
    rotation:
      max_file_size_mb: 100         # Rotate at 100MB
      max_files: 10                 # Keep 10 files (1GB total)

    # Performance (future)
    async_logging: false            # Sync by default
    buffer_size: 1024               # Flush every 1KB
```

### Disabling Specific Events

To reduce log volume, disable specific event types:

```yaml
events:
  user_input: true          # Keep user input
  nl_results: true          # Keep quality metrics
  execution_results: true   # Keep outcomes
  errors: true              # Keep errors
  orchestrator_prompts: false   # Disable (verbose)
  implementer_responses: false  # Disable (verbose)
```

### Adjusting Log Rotation

Control disk usage with rotation settings:

```yaml
rotation:
  max_file_size_mb: 50   # Smaller files (50MB instead of 100MB)
  max_files: 5           # Keep fewer files (250MB total instead of 1GB)
```

---

## Privacy Protection

### Automatic Redaction

All sensitive data is automatically redacted:

**PII (Personal Identifiable Information):**
- Email addresses → `[EMAIL]`
- IP addresses → `[IP]`
- SSN (Social Security Numbers) → `[SSN]`
- Phone numbers → `[PHONE]`

**Secrets:**
- API keys (OpenAI-style) → `[API_KEY]`
- GitHub tokens → `[GH_TOKEN]`
- Generic long tokens (40+ chars) → `[TOKEN]`

**Example:**

Input: `"Contact me at john@example.com using token sk-abc123..."`

Logged: `"Contact me at [EMAIL] using token [API_KEY]"`

### UUID Safety

Session IDs (UUIDs) are **NOT** redacted, ensuring session tracking remains functional.

---

## Log Analysis

### Common Queries

#### 1. View All Errors

```bash
cat ~/obra-runtime/logs/production.jsonl | jq 'select(.type == "error")'
```

#### 2. Track Quality Metrics

```bash
# NL processing quality
cat ~/obra-runtime/logs/production.jsonl | \
  jq 'select(.type == "nl_result") | {confidence, validation, duration_ms}'

# Average confidence
cat ~/obra-runtime/logs/production.jsonl | \
  jq -s 'map(select(.type == "nl_result")) | map(.confidence) | add / length'
```

#### 3. Monitor Performance

```bash
# Average NL processing time
cat ~/obra-runtime/logs/production.jsonl | \
  jq -s 'map(select(.type == "nl_result")) | map(.duration_ms) | add / length'

# Average execution time
cat ~/obra-runtime/logs/production.jsonl | \
  jq -s 'map(select(.type == "execution_result")) | map(.total_duration_ms) | add / length'
```

#### 4. Track a Specific Session

```bash
SESSION_ID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
cat ~/obra-runtime/logs/production.jsonl | jq "select(.session == \"$SESSION_ID\")"
```

#### 5. Count Events by Type

```bash
cat ~/obra-runtime/logs/production.jsonl | \
  jq -s 'group_by(.type) | map({type: .[0].type, count: length})'
```

#### 6. Failed Operations

```bash
cat ~/obra-runtime/logs/production.jsonl | \
  jq 'select(.type == "execution_result" and .success == false)'
```

### Analysis Scripts

Create custom analysis scripts for recurring queries:

```bash
#!/bin/bash
# analyze_quality.sh - Analyze NL quality metrics

LOG_FILE="${1:-~/obra-runtime/logs/production.jsonl}"

echo "=== NL Quality Analysis ==="
echo

echo "Average Confidence:"
cat "$LOG_FILE" | \
  jq -s 'map(select(.type == "nl_result")) | map(.confidence) | add / length'

echo
echo "Validation Pass Rate:"
cat "$LOG_FILE" | \
  jq -s 'map(select(.type == "nl_result")) |
         {passed: map(select(.validation == "passed")) | length,
          total: length} |
         (.passed / .total * 100)'

echo
echo "Average Processing Time (ms):"
cat "$LOG_FILE" | \
  jq -s 'map(select(.type == "nl_result")) | map(.duration_ms) | add / length'
```

---

## Troubleshooting

### Log File Not Created

**Symptom:** No log file at `~/obra-runtime/logs/production.jsonl`

**Solutions:**
1. Check if production logging is enabled in `config/config.yaml`
2. Verify directory permissions:
   ```bash
   mkdir -p ~/obra-runtime/logs
   chmod 755 ~/obra-runtime/logs
   ```
3. Check logs for initialization errors:
   ```bash
   tail -50 ~/obra-runtime/logs/orchestrator.log | grep "ProductionLogger"
   ```

### High Disk Usage

**Symptom:** Logs consuming too much disk space

**Solutions:**
1. Reduce log rotation limits:
   ```yaml
   rotation:
     max_file_size_mb: 50
     max_files: 5
   ```
2. Disable verbose events:
   ```yaml
   events:
     orchestrator_prompts: false
     implementer_responses: false
   ```
3. Archive and compress old logs:
   ```bash
   gzip ~/obra-runtime/logs/production.jsonl.1
   ```

### Missing Events

**Symptom:** Expected events not appearing in logs

**Solutions:**
1. Check event filtering in config:
   ```yaml
   events:
     user_input: true  # Ensure not disabled
   ```
2. Verify session is active:
   ```bash
   tail -5 ~/obra-runtime/logs/production.jsonl | jq '.session'
   ```

### Privacy Concerns

**Symptom:** Sensitive data appearing in logs despite redaction

**Solutions:**
1. Verify privacy settings:
   ```yaml
   privacy:
     redact_pii: true
     redact_secrets: true
   ```
2. Add custom redaction patterns (future feature)
3. Disable production logging entirely:
   ```yaml
   enabled: false
   ```

---

## Performance Impact

Production logging is designed for minimal performance overhead:

**Measured Impact:**
- **Latency**: < 5ms per log event (P95)
- **Throughput**: > 1000 events/second
- **Memory**: < 10MB baseline
- **Disk I/O**: Buffered writes (1KB buffer)

**Recommendations:**
- Keep enabled in production (observability > minimal overhead)
- Disable only in performance-critical, privacy-sensitive environments
- Use log rotation to prevent unbounded disk growth

---

## Best Practices

### 1. Regular Log Review

Schedule periodic log reviews to:
- Monitor quality trends (confidence scores, validation rates)
- Identify recurring errors
- Optimize prompts based on low-confidence queries

### 2. Archive Old Logs

Compress and archive rotated logs:

```bash
# Monthly archival script
cd ~/obra-runtime/logs
gzip production.jsonl.*
mkdir -p archive/$(date +%Y-%m)
mv production.jsonl.*.gz archive/$(date +%Y-%m)/
```

### 3. Alert on Errors

Set up automated alerts for error spikes:

```bash
#!/bin/bash
# alert_on_errors.sh - Alert if error rate > 5%

ERROR_COUNT=$(cat ~/obra-runtime/logs/production.jsonl | jq -s 'map(select(.type == "error")) | length')
TOTAL_COUNT=$(cat ~/obra-runtime/logs/production.jsonl | jq -s 'length')
ERROR_RATE=$(echo "scale=2; $ERROR_COUNT / $TOTAL_COUNT * 100" | bc)

if (( $(echo "$ERROR_RATE > 5" | bc -l) )); then
  echo "ALERT: Error rate is ${ERROR_RATE}% (threshold: 5%)"
  # Send notification (email, Slack, etc.)
fi
```

### 4. Privacy Compliance

For GDPR/HIPAA compliance:
1. Enable full redaction:
   ```yaml
   privacy:
     redact_pii: true
     redact_secrets: true
   ```
2. Document data retention policy
3. Implement log deletion after retention period:
   ```bash
   # Delete logs older than 90 days
   find ~/obra-runtime/logs -name "production.jsonl.*" -mtime +90 -delete
   ```

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Section 12: Production Monitoring
- [README.md](../../README.md) - Production Monitoring overview
- [Session Management Guide](SESSION_MANAGEMENT_GUIDE.md) - Session tracking details
- [Interactive Mode Guide](INTERACTIVE_STREAMING_QUICKREF.md) - Interactive commands

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs: `tail -50 ~/obra-runtime/logs/orchestrator.log`
3. Report issues: https://github.com/Omar-Unpossible/claude_code_orchestrator/issues

---

**Version**: 1.8.0
**Last Updated**: November 15, 2025
