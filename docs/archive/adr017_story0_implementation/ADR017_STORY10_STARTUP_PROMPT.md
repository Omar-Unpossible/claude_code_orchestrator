# ADR-017 Story 10 Startup Prompt

**Story 10 of 10** (ADR-017 Implementation - FINAL STORY for v1.7.1)

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 1-9 are complete (v1.7.0 released, v1.7.1 Story 9 complete). Now implement Story 10 (Observability Enhancements - FINAL).

---

## What You're Building

**Story 10**: Observability & Monitoring Enhancements (8 hours)

**Purpose**: Enhance observability infrastructure with production-grade monitoring, alerting, and debugging capabilities. Build on the basic logging/metrics foundation to provide comprehensive system health visibility.

**Key Objectives**:
- Enhanced structured logging with correlation IDs
- Metrics v2 with alerting thresholds and trend detection
- CLI commands for health checks, metrics viewing, and log querying
- Production-ready monitoring and debugging tools

**Part of**: v1.7.1 (follow-up release after v1.7.0)

---

## What's Already Complete

### Stories 1-9 ✅
- **v1.7.0 Released**: Unified execution architecture fully implemented
  - All NL commands route through orchestrator
  - IntentToTaskConverter and NLQueryHelper components
  - Integration testing and documentation complete
  - Destructive operation breakpoints (Story 8)

- **v1.7.1 Story 9 Complete**: Enhanced confirmation workflow UI
  - Color-coded prompts with cascade implications
  - Dry-run simulation mode
  - Contextual help system

### Current Logging/Metrics (Basic)
The system has basic structured logging and metrics collection from earlier implementation:
- JSON-formatted log events
- Basic metrics collection (LLM requests, agent executions)
- Simple health check endpoint

**What's Missing** (Story 10 adds):
- ❌ Correlation IDs for cross-component request tracking
- ❌ Log filtering and querying capabilities
- ❌ Alerting thresholds for degraded service detection
- ❌ Trend analysis and anomaly detection
- ❌ Production-ready CLI commands (`obra health`, `obra metrics`, `obra logs`)

---

## The Problem

Current observability has critical gaps:

1. **No Request Tracing**: Can't follow a single NL command through entire pipeline (NL processor → orchestrator → agent → LLM)
2. **No Log Filtering**: 1000s of log entries with no way to query specific events or time ranges
3. **No Alerting**: System can degrade (LLM latency spike, agent failures) without detection
4. **Manual Debugging**: Must read raw logs to troubleshoot issues
5. **No Health Visibility**: Can't quickly check if system is healthy or what's degraded

**Example Pain Point**:
```
User reports: "My NL command took 30 seconds"

Current debugging process:
1. Grep through logs for timestamps (tedious)
2. Find all related log entries manually (error-prone)
3. No correlation between NL → orchestrator → agent → LLM
4. No metrics showing if this is systemic or one-off
5. Takes 30+ minutes to diagnose

With Story 10:
$ obra logs --correlation-id=abc123
# Shows entire request flow in seconds
$ obra metrics --window=1h
# Shows if latency spike is systemic
# Takes < 2 minutes to diagnose
```

---

## The Solution

### Enhanced Structured Logging (Correlation IDs)

**Concept**: Every operation gets a unique correlation ID that propagates across all components.

**Implementation**:
```python
# src/core/logging_config.py
import threading
from contextvars import ContextVar

# Thread-safe correlation ID storage
_correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)

class CorrelationContext:
    """Context manager for automatic correlation ID propagation."""

    def __init__(self, correlation_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.token = None

    def __enter__(self):
        self.token = _correlation_id.set(self.correlation_id)
        return self

    def __exit__(self, *args):
        _correlation_id.reset(self.token)

# Enhanced logger that automatically includes correlation ID
def get_logger(name: str):
    logger = logging.getLogger(name)
    # Add filter that injects correlation_id into all log records
    logger.addFilter(CorrelationIDFilter())
    return logger
```

**Usage**:
```python
# In orchestrator.py
with CorrelationContext() as ctx:
    logger.info("Starting NL command execution",
                event="nl_command_start",
                command=message)
    # All subsequent logs include correlation_id=ctx.correlation_id
    result = self.execute_nl_command(message)
    logger.info("NL command completed",
                event="nl_command_complete",
                success=True)
```

**Result**: All logs for a single request have same correlation_id, enabling instant filtering.

---

### Metrics v2 with Alerting

**Alerting Thresholds**:
```python
# src/core/metrics.py
ALERTING_THRESHOLDS = {
    'llm_success_rate': {
        'warning': 0.95,   # Alert if < 95%
        'critical': 0.90   # Critical if < 90%
    },
    'llm_latency_p95': {
        'warning': 3000,   # 3s
        'critical': 5000   # 5s
    },
    'agent_success_rate': {
        'warning': 0.90,
        'critical': 0.80
    }
}

class MetricsCollector:
    def check_health(self) -> HealthStatus:
        """Check if metrics exceed alerting thresholds."""
        status = HealthStatus.HEALTHY
        alerts = []

        # Check LLM success rate
        llm_success = self.get_llm_success_rate(window='5m')
        if llm_success < ALERTING_THRESHOLDS['llm_success_rate']['critical']:
            status = HealthStatus.UNHEALTHY
            alerts.append(f"LLM success rate critical: {llm_success:.1%}")
        elif llm_success < ALERTING_THRESHOLDS['llm_success_rate']['warning']:
            status = min(status, HealthStatus.DEGRADED)
            alerts.append(f"LLM success rate low: {llm_success:.1%}")

        # Check LLM latency...
        # Check agent success rate...

        return HealthStatus(status=status, alerts=alerts)
```

**Trend Detection**:
```python
def detect_trends(self, metric: str, window: str = '15m') -> List[Trend]:
    """Detect significant trends (degradation or improvement)."""
    current = self.get_metric(metric, window=window)
    previous = self.get_metric(metric, window=window, offset=window)

    change_pct = (current - previous) / previous

    trends = []
    if metric == 'llm_latency_p95' and change_pct > 0.5:
        trends.append(Trend(
            metric='llm_latency_p95',
            direction='increasing',
            magnitude=change_pct,
            severity='warning',
            message=f"LLM latency increased {change_pct:.1%} in last {window}"
        ))

    return trends
```

---

### CLI Commands

**1. `obra health` - System Health Check**
```bash
$ obra health

Status: HEALTHY ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LLM: Ollama (qwen2.5-coder:32b)
  ✓ Available: Yes
  ✓ Success Rate: 98.2% (last 5 min)
  ✓ Latency P95: 1234ms

Agent: Claude Code Local
  ✓ Available: Yes
  ✓ Success Rate: 95.1%

Database: SQLite
  ✓ Available: Yes

Overall: All systems operational
```

**Degraded State Example**:
```bash
$ obra health

Status: DEGRADED ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LLM: Ollama (qwen2.5-coder:32b)
  ⚠ Available: Yes
  ⚠ Success Rate: 92.3% (last 5 min) [WARNING: Below 95% threshold]
  ⚠ Latency P95: 3456ms [WARNING: Above 3000ms threshold]

Agent: Claude Code Local
  ✓ Available: Yes
  ✓ Success Rate: 96.8%

Database: SQLite
  ✓ Available: Yes

Alerts:
  ⚠ LLM success rate below threshold (92.3% < 95%)
  ⚠ LLM latency elevated (3456ms > 3000ms warning)

Recommendations:
  • Check LLM service load (may need restart)
  • Review recent error logs: obra logs --level=ERROR --since='5m'
  • Check for network issues or resource constraints
```

**2. `obra metrics` - Detailed Metrics**
```bash
$ obra metrics --window=1h

LLM Metrics (last 1 hour):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Requests: 156
  Success Rate: 97.4% (↑ 2.0% from previous hour)

  Latency:
    P50: 845ms
    P95: 1523ms (↓ 200ms)
    P99: 2891ms

  By Provider:
    Ollama: 143 requests (91.7%)
    OpenAI Codex: 13 requests (8.3%)

Agent Metrics (last 1 hour):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Executions: 42
  Success Rate: 95.2%
  Avg Duration: 23.4s
  Files Modified: 86

NL Command Metrics (last 1 hour):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Commands: 58
  Success Rate: 96.6%
  Avg Latency: 1234ms

  By Operation:
    CREATE: 28 (48.3%)
    QUERY: 18 (31.0%)
    UPDATE: 8 (13.8%)
    DELETE: 4 (6.9%)
```

**3. `obra logs` - Log Querying**
```bash
# Query by event type
$ obra logs --event=nl_command --since='5m'
2025-11-13T22:45:12Z [nl_command] correlation_id=abc123
  command: "create epic for auth"
  intent: COMMAND
  operation: CREATE
  success: true
  latency_ms: 234

# Query by correlation ID (trace full request)
$ obra logs --correlation-id=abc123
2025-11-13T22:45:12Z [nl_command] correlation_id=abc123
  event: nl_command_start
  command: "create epic for auth"

2025-11-13T22:45:12Z [llm_request] correlation_id=abc123
  event: intent_classification
  provider: ollama
  latency_ms: 156

2025-11-13T22:45:13Z [orchestrator] correlation_id=abc123
  event: task_created
  task_id: 42

2025-11-13T22:45:15Z [agent_execution] correlation_id=abc123
  event: agent_complete
  duration_s: 2.1
  files_modified: 3

# Query errors only
$ obra logs --level=ERROR --since='1h'
# Shows only ERROR level logs from last hour
```

---

## Implementation Plan

### Step 1: Enhanced Logging with Correlation IDs

**File**: `src/core/logging_config.py`

**Add**:
```python
import uuid
from contextvars import ContextVar
from typing import Optional

# Thread-safe correlation ID storage
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

class CorrelationContext:
    """Context manager for correlation ID propagation."""

    def __init__(self, correlation_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.token = None

    def __enter__(self):
        self.token = _correlation_id.set(self.correlation_id)
        return self

    def __exit__(self, *args):
        if self.token:
            _correlation_id.reset(self.token)

class CorrelationIDFilter(logging.Filter):
    """Inject correlation ID into all log records."""

    def filter(self, record):
        record.correlation_id = _correlation_id.get() or 'none'
        return True

def get_logger(name: str) -> logging.Logger:
    """Get logger with correlation ID support."""
    logger = logging.getLogger(name)

    # Add correlation ID filter if not already present
    if not any(isinstance(f, CorrelationIDFilter) for f in logger.filters):
        logger.addFilter(CorrelationIDFilter())

    return logger

# Log filtering utilities
def query_logs(
    event: Optional[str] = None,
    level: Optional[str] = None,
    correlation_id: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """Query structured logs with filters."""
    # Implementation: Read JSONL log file, apply filters, return matching entries
    pass
```

**Integration Points**:
1. `src/orchestrator.py::execute_nl_command()` - Wrap in CorrelationContext
2. `src/orchestrator.py::execute_task()` - Use existing correlation_id if present
3. `src/nl/nl_command_processor.py::process()` - Start correlation context
4. `src/llm/local_llm_interface.py` - Log with correlation ID
5. `src/agents/claude_code_local_agent.py` - Log with correlation ID

---

### Step 2: Metrics v2 with Alerting

**File**: `src/core/metrics.py`

**Add**:
```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class Trend:
    metric: str
    direction: str  # 'increasing' | 'decreasing'
    magnitude: float  # % change
    severity: str  # 'info' | 'warning' | 'critical'
    message: str

ALERTING_THRESHOLDS = {
    'llm_success_rate': {'warning': 0.95, 'critical': 0.90},
    'llm_latency_p95': {'warning': 3000, 'critical': 5000},
    'agent_success_rate': {'warning': 0.90, 'critical': 0.80}
}

class MetricsCollector:
    # ... existing code ...

    def check_health(self) -> Dict[str, Any]:
        """Check system health with alerting thresholds."""
        status = HealthStatus.HEALTHY
        alerts = []

        # Check LLM metrics
        llm_success = self.get_llm_success_rate(window='5m')
        llm_latency = self.get_llm_latency_p95(window='5m')

        if llm_success < ALERTING_THRESHOLDS['llm_success_rate']['critical']:
            status = HealthStatus.UNHEALTHY
            alerts.append(f"LLM success rate critical: {llm_success:.1%}")
        elif llm_success < ALERTING_THRESHOLDS['llm_success_rate']['warning']:
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
            alerts.append(f"LLM success rate low: {llm_success:.1%}")

        if llm_latency > ALERTING_THRESHOLDS['llm_latency_p95']['critical']:
            status = HealthStatus.UNHEALTHY
            alerts.append(f"LLM latency critical: {llm_latency}ms")
        elif llm_latency > ALERTING_THRESHOLDS['llm_latency_p95']['warning']:
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
            alerts.append(f"LLM latency elevated: {llm_latency}ms")

        # Check agent metrics...

        return {
            'status': status.value,
            'alerts': alerts,
            'llm': self._get_llm_health(),
            'agent': self._get_agent_health(),
            'database': self._get_database_health()
        }

    def detect_trends(self, metric: str, window: str = '15m') -> List[Trend]:
        """Detect trends in metrics (increasing/decreasing)."""
        current = self.get_metric(metric, window=window)
        previous = self.get_metric(metric, window=window, offset=window)

        if previous == 0:
            return []

        change_pct = (current - previous) / previous
        trends = []

        # Define trend detection rules
        if abs(change_pct) > 0.2:  # 20% change
            severity = 'warning' if abs(change_pct) > 0.5 else 'info'
            direction = 'increasing' if change_pct > 0 else 'decreasing'

            trends.append(Trend(
                metric=metric,
                direction=direction,
                magnitude=abs(change_pct),
                severity=severity,
                message=f"{metric} {direction} by {abs(change_pct):.1%}"
            ))

        return trends
```

---

### Step 3: CLI Commands

**File**: `src/cli.py`

**Add Commands**:
```python
import click
from src.core.logging_config import query_logs
from src.core.metrics import MetricsCollector, HealthStatus

@cli.command()
def health():
    """Check system health with detailed status."""
    metrics = MetricsCollector()
    health_data = metrics.check_health()

    # Determine status symbol
    if health_data['status'] == 'healthy':
        status_symbol = '✅'
        status_color = 'green'
    elif health_data['status'] == 'degraded':
        status_symbol = '⚠️'
        status_color = 'yellow'
    else:
        status_symbol = '🔴'
        status_color = 'red'

    # Display health status
    click.echo()
    click.secho(f"Status: {health_data['status'].upper()} {status_symbol}",
                fg=status_color, bold=True)
    click.echo("━" * 50)
    click.echo()

    # LLM health
    llm = health_data['llm']
    click.echo("LLM: Ollama (qwen2.5-coder:32b)")
    _display_metric("Available", llm['available'])
    _display_metric("Success Rate", f"{llm['success_rate']:.1%}")
    _display_metric("Latency P95", f"{llm['latency_p95']}ms")
    click.echo()

    # Agent health
    agent = health_data['agent']
    click.echo("Agent: Claude Code Local")
    _display_metric("Available", agent['available'])
    _display_metric("Success Rate", f"{agent['success_rate']:.1%}")
    click.echo()

    # Database health
    db = health_data['database']
    click.echo("Database: SQLite")
    _display_metric("Available", db['available'])
    click.echo()

    # Alerts
    if health_data['alerts']:
        click.echo("Alerts:")
        for alert in health_data['alerts']:
            click.secho(f"  {status_symbol} {alert}", fg='yellow')
        click.echo()

@cli.command()
@click.option('--window', default='1h', help='Time window (e.g., 1h, 30m)')
def metrics(window):
    """Display detailed system metrics."""
    metrics_collector = MetricsCollector()

    click.echo()
    click.secho(f"LLM Metrics (last {window}):", bold=True)
    click.echo("━" * 50)

    # Get LLM metrics
    llm_data = metrics_collector.get_llm_metrics(window=window)
    click.echo(f"  Requests: {llm_data['count']}")
    click.echo(f"  Success Rate: {llm_data['success_rate']:.1%}")
    click.echo()
    click.echo("  Latency:")
    click.echo(f"    P50: {llm_data['latency_p50']}ms")
    click.echo(f"    P95: {llm_data['latency_p95']}ms")
    click.echo(f"    P99: {llm_data['latency_p99']}ms")
    click.echo()

    # Similar for agent and NL metrics...

@cli.command()
@click.option('--event', help='Filter by event type')
@click.option('--level', help='Filter by log level')
@click.option('--correlation-id', help='Filter by correlation ID')
@click.option('--since', default='1h', help='Time window')
@click.option('--limit', default=100, help='Max entries')
def logs(event, level, correlation_id, since, limit):
    """Query structured logs with filters."""
    results = query_logs(
        event=event,
        level=level,
        correlation_id=correlation_id,
        since=since,
        limit=limit
    )

    if not results:
        click.echo("No matching log entries found.")
        return

    for entry in results:
        timestamp = entry['timestamp']
        event_name = entry['event']
        corr_id = entry.get('correlation_id', 'none')

        click.echo(f"{timestamp} [{event_name}] correlation_id={corr_id}")

        # Display relevant fields
        for key, value in entry.items():
            if key not in ['timestamp', 'event', 'correlation_id']:
                click.echo(f"  {key}: {value}")
        click.echo()
```

---

## Acceptance Criteria

✅ **Enhanced Logging**:
- [ ] CorrelationContext context manager implemented
- [ ] Correlation IDs propagate across all components
- [ ] All critical paths wrapped in CorrelationContext
- [ ] Log filtering by event/level/correlation/time implemented

✅ **Metrics v2**:
- [ ] Alerting thresholds defined for LLM/agent metrics
- [ ] Health check with HEALTHY/DEGRADED/UNHEALTHY states
- [ ] Trend detection with magnitude and severity
- [ ] Recommendations for degraded states

✅ **CLI Commands**:
- [ ] `obra health` command displays system health
- [ ] `obra metrics` command shows detailed metrics
- [ ] `obra logs` command queries logs with filters
- [ ] Color-coded output for readability

✅ **Testing**:
- [ ] **20 unit tests** for logging/metrics/CLI
- [ ] **8 integration tests** for end-to-end correlation tracking
- [ ] All tests passing

✅ **Documentation**:
- [ ] Updated docs/guides with observability guide
- [ ] CHANGELOG.md updated for v1.7.1 final
- [ ] Examples and troubleshooting guide

---

## Validation Commands

**Test correlation ID propagation**:
```bash
# Execute NL command and check logs include correlation ID
$ python -m src.cli interactive
orchestrator> create epic for testing correlation
# Check logs: all entries for this command should have same correlation_id
```

**Test health check**:
```bash
$ obra health
# Should show system status with detailed metrics
```

**Test metrics viewing**:
```bash
$ obra metrics --window=1h
# Should show aggregated metrics with trends
```

**Test log querying**:
```bash
$ obra logs --event=nl_command --since='5m'
# Should show recent NL commands with correlation IDs
```

---

## Common Pitfalls to Avoid

1. ❌ **Don't break existing logging**: Ensure backward compatibility
2. ❌ **Don't hardcode thresholds**: Use configuration for alerting thresholds
3. ❌ **Don't forget thread safety**: Use ContextVar for correlation IDs, not thread-local
4. ❌ **Don't query large log files inefficiently**: Use streaming/indexing for log queries
5. ❌ **Don't skip CLI testing**: Test all CLI commands work correctly

---

## Upon Completion of Story 10

**Status**: Story 10 of 10 COMPLETE! 🎉 **ADR-017 FULLY IMPLEMENTED**

After Story 10, you will have:
- ✅ Complete observability infrastructure
- ✅ Production-ready monitoring and alerting
- ✅ Powerful debugging tools (correlation IDs, log querying)
- ✅ Health visibility and trend detection
- ✅ **ADR-017 fully implemented** (all 10 stories complete!)

**Next Steps**:
1. Release v1.7.1 final with observability
2. User acceptance testing
3. Create production deployment guide
4. Set up monitoring dashboards (optional)
5. Document troubleshooting procedures

**ADR-017 Implementation Complete!** ✅

---

**Ready to start? Implement Story 10: Observability & Monitoring Enhancements (FINAL).**
