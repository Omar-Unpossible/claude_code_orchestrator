"""Metrics collection and health checks for Obra.

Provides metrics aggregation, health check endpoints, and system monitoring.

Metrics:
- llm_requests: Count, success rate, latency percentiles
- agent_executions: Count, success rate, avg duration, files modified
- nl_commands: Count, success rate, avg latency, by operation type

Health Check:
- Status: healthy | degraded | unhealthy
- LLM availability and success rate
- Agent availability
- Database availability

Usage:
    from src.core.metrics import get_metrics_collector

    metrics = get_metrics_collector()
    metrics.record_llm_request(
        provider='ollama',
        latency_ms=1234,
        success=True
    )

    health = metrics.get_health_status()
    print(health['status'])  # 'healthy'
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import threading


# Alerting thresholds
ALERTING_THRESHOLDS = {
    'llm_success_rate': {
        'warning': 0.95,
        'critical': 0.90
    },
    'llm_latency_p95': {
        'warning': 3000,  # ms
        'critical': 5000  # ms
    },
    'agent_success_rate': {
        'warning': 0.90,
        'critical': 0.80
    }
}


class HealthStatus(Enum):
    """System health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class Trend:
    """Metric trend information."""
    metric: str
    direction: str  # 'increasing' | 'decreasing' | 'stable'
    magnitude: float  # % change
    severity: str  # 'info' | 'warning' | 'critical'
    message: str


class MetricsCollector:
    """Collects and aggregates system metrics."""

    def __init__(self, window_minutes: int = 5):
        """Initialize metrics collector.

        Args:
            window_minutes: Rolling window for metrics (default: 5 minutes)
        """
        self.window_minutes = window_minutes
        self.window_seconds = window_minutes * 60

        # Thread-safe locks
        self.lock = threading.RLock()

        # LLM metrics
        self.llm_requests = deque()  # (timestamp, provider, latency_ms, success)

        # Agent metrics
        self.agent_executions = deque()  # (timestamp, agent_type, duration_s, success, file_count)

        # NL command metrics
        self.nl_commands = deque()  # (timestamp, operation, latency_ms, success)

        # Aggregated counters (since startup)
        self.total_llm_requests = 0
        self.total_agent_executions = 0
        self.total_nl_commands = 0

    def _cleanup_old_metrics(self):
        """Remove metrics outside rolling window."""
        cutoff_time = time.time() - self.window_seconds

        with self.lock:
            # Cleanup LLM requests
            while self.llm_requests and self.llm_requests[0][0] < cutoff_time:
                self.llm_requests.popleft()

            # Cleanup agent executions
            while self.agent_executions and self.agent_executions[0][0] < cutoff_time:
                self.agent_executions.popleft()

            # Cleanup NL commands
            while self.nl_commands and self.nl_commands[0][0] < cutoff_time:
                self.nl_commands.popleft()

    def record_llm_request(
        self,
        provider: str,
        latency_ms: float,
        success: bool,
        model: Optional[str] = None
    ):
        """Record LLM request metric.

        Args:
            provider: LLM provider (ollama, openai-codex)
            latency_ms: Request latency in milliseconds
            success: Whether request succeeded
            model: Model name (optional)
        """
        with self.lock:
            timestamp = time.time()
            self.llm_requests.append((timestamp, provider, latency_ms, success, model))
            self.total_llm_requests += 1

        # Cleanup old metrics
        self._cleanup_old_metrics()

    def record_agent_execution(
        self,
        agent_type: str,
        duration_s: float,
        success: bool,
        files_modified: int = 0
    ):
        """Record agent execution metric.

        Args:
            agent_type: Agent type (claude-code-local, claude-code-ssh)
            duration_s: Execution duration in seconds
            success: Whether execution succeeded
            files_modified: Number of files modified
        """
        with self.lock:
            timestamp = time.time()
            self.agent_executions.append(
                (timestamp, agent_type, duration_s, success, files_modified)
            )
            self.total_agent_executions += 1

        self._cleanup_old_metrics()

    def record_nl_command(
        self,
        operation: str,
        latency_ms: float,
        success: bool
    ):
        """Record NL command metric.

        Args:
            operation: Operation type (CREATE, UPDATE, DELETE, QUERY)
            latency_ms: Processing latency in milliseconds
            success: Whether command succeeded
        """
        with self.lock:
            timestamp = time.time()
            self.nl_commands.append((timestamp, operation, latency_ms, success))
            self.total_nl_commands += 1

        self._cleanup_old_metrics()

    def get_llm_metrics(self) -> Dict[str, Any]:
        """Get LLM metrics for rolling window.

        Returns:
            Dictionary with LLM metrics:
            - count: Total requests in window
            - success_rate: Percentage of successful requests
            - latency_p50: 50th percentile latency (ms)
            - latency_p95: 95th percentile latency (ms)
            - latency_p99: 99th percentile latency (ms)
            - avg_latency: Average latency (ms)
            - by_provider: Metrics grouped by provider
        """
        self._cleanup_old_metrics()

        with self.lock:
            if not self.llm_requests:
                return {
                    'count': 0,
                    'success_rate': 0.0,
                    'latency_p50': 0.0,
                    'latency_p95': 0.0,
                    'latency_p99': 0.0,
                    'avg_latency': 0.0,
                    'by_provider': {}
                }

            # Extract data
            successes = sum(1 for _, _, _, success, _ in self.llm_requests if success)
            latencies = [latency for _, _, latency, _, _ in self.llm_requests]

            # Calculate metrics
            count = len(self.llm_requests)
            success_rate = successes / count if count > 0 else 0.0

            sorted_latencies = sorted(latencies)
            latency_p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
            latency_p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            latency_p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            avg_latency = sum(latencies) / len(latencies)

            # Group by provider
            by_provider = defaultdict(lambda: {'count': 0, 'success': 0})
            for _, provider, _, success, _ in self.llm_requests:
                by_provider[provider]['count'] += 1
                if success:
                    by_provider[provider]['success'] += 1

            # Calculate provider success rates
            provider_metrics = {}
            for provider, data in by_provider.items():
                provider_metrics[provider] = {
                    'count': data['count'],
                    'success_rate': data['success'] / data['count']
                }

            return {
                'count': count,
                'success_rate': success_rate,
                'latency_p50': latency_p50,
                'latency_p95': latency_p95,
                'latency_p99': latency_p99,
                'avg_latency': avg_latency,
                'by_provider': provider_metrics
            }

    def get_agent_metrics(self) -> Dict[str, Any]:
        """Get agent execution metrics for rolling window.

        Returns:
            Dictionary with agent metrics:
            - count: Total executions in window
            - success_rate: Percentage of successful executions
            - avg_duration: Average duration (seconds)
            - total_files_modified: Total files modified
        """
        self._cleanup_old_metrics()

        with self.lock:
            if not self.agent_executions:
                return {
                    'count': 0,
                    'success_rate': 0.0,
                    'avg_duration': 0.0,
                    'total_files_modified': 0
                }

            # Extract data
            successes = sum(1 for _, _, _, success, _ in self.agent_executions if success)
            durations = [duration for _, _, duration, _, _ in self.agent_executions]
            files_modified = sum(files for _, _, _, _, files in self.agent_executions)

            count = len(self.agent_executions)
            success_rate = successes / count if count > 0 else 0.0
            avg_duration = sum(durations) / len(durations) if durations else 0.0

            return {
                'count': count,
                'success_rate': success_rate,
                'avg_duration': avg_duration,
                'total_files_modified': files_modified
            }

    def get_nl_command_metrics(self) -> Dict[str, Any]:
        """Get NL command metrics for rolling window.

        Returns:
            Dictionary with NL command metrics:
            - count: Total commands in window
            - success_rate: Percentage of successful commands
            - avg_latency: Average latency (ms)
            - by_operation: Metrics grouped by operation type
        """
        self._cleanup_old_metrics()

        with self.lock:
            if not self.nl_commands:
                return {
                    'count': 0,
                    'success_rate': 0.0,
                    'avg_latency': 0.0,
                    'by_operation': {}
                }

            # Extract data
            successes = sum(1 for _, _, _, success in self.nl_commands if success)
            latencies = [latency for _, _, latency, _ in self.nl_commands]

            count = len(self.nl_commands)
            success_rate = successes / count if count > 0 else 0.0
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

            # Group by operation
            by_operation = defaultdict(lambda: {'count': 0, 'success': 0})
            for _, operation, _, success in self.nl_commands:
                by_operation[operation]['count'] += 1
                if success:
                    by_operation[operation]['success'] += 1

            # Calculate operation success rates
            operation_metrics = {}
            for operation, data in by_operation.items():
                operation_metrics[operation] = {
                    'count': data['count'],
                    'success_rate': data['success'] / data['count']
                }

            return {
                'count': count,
                'success_rate': success_rate,
                'avg_latency': avg_latency,
                'by_operation': operation_metrics
            }

    def detect_trends(self, metric: str = 'llm_latency_p95', window: str = '15m') -> List[Trend]:
        """Detect trends in metrics over time.

        Args:
            metric: Metric to analyze ('llm_latency_p95', 'llm_success_rate', etc.)
            window: Time window for trend detection (default: 15m)

        Returns:
            List of detected trends
        """
        trends = []

        # For simplicity, we'll compare current window vs previous window
        # In production, you'd use more sophisticated trend detection

        try:
            if metric == 'llm_latency_p95':
                current = self.get_llm_metrics()['latency_p95']

                # Get historical data (simplified - in production use time-series DB)
                # For now, compare with warning threshold
                if current > ALERTING_THRESHOLDS['llm_latency_p95']['critical']:
                    trends.append(Trend(
                        metric='llm_latency_p95',
                        direction='increasing',
                        magnitude=(current / ALERTING_THRESHOLDS['llm_latency_p95']['warning']) - 1.0,
                        severity='critical',
                        message=f"LLM latency critically high: {current:.0f}ms"
                    ))
                elif current > ALERTING_THRESHOLDS['llm_latency_p95']['warning']:
                    trends.append(Trend(
                        metric='llm_latency_p95',
                        direction='increasing',
                        magnitude=(current / ALERTING_THRESHOLDS['llm_latency_p95']['warning']) - 1.0,
                        severity='warning',
                        message=f"LLM latency elevated: {current:.0f}ms"
                    ))

            elif metric == 'llm_success_rate':
                current = self.get_llm_metrics()['success_rate']

                if current < ALERTING_THRESHOLDS['llm_success_rate']['critical']:
                    trends.append(Trend(
                        metric='llm_success_rate',
                        direction='decreasing',
                        magnitude=1.0 - (current / ALERTING_THRESHOLDS['llm_success_rate']['warning']),
                        severity='critical',
                        message=f"LLM success rate critically low: {current:.1%}"
                    ))
                elif current < ALERTING_THRESHOLDS['llm_success_rate']['warning']:
                    trends.append(Trend(
                        metric='llm_success_rate',
                        direction='decreasing',
                        magnitude=1.0 - (current / ALERTING_THRESHOLDS['llm_success_rate']['warning']),
                        severity='warning',
                        message=f"LLM success rate below threshold: {current:.1%}"
                    ))

        except Exception:
            # Return empty list on error
            pass

        return trends

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status with detailed information.

        Returns:
            Dictionary with health status:
            - status: 'healthy' | 'degraded' | 'unhealthy'
            - alerts: List of active alerts
            - llm: Detailed LLM health
            - agent: Detailed agent health
            - database: Detailed database health
            - recommendations: List of recommended actions
            - timestamp: ISO timestamp
        """
        llm_metrics = self.get_llm_metrics()
        agent_metrics = self.get_agent_metrics()

        # Determine LLM health
        llm_available = llm_metrics['count'] > 0
        llm_success_rate = llm_metrics['success_rate']
        llm_latency_p95 = llm_metrics['latency_p95']

        # Determine agent health
        agent_available = agent_metrics['count'] > 0
        agent_success_rate = agent_metrics['success_rate']

        # Determine database health (assume healthy if no errors)
        database_available = True  # TODO: Add database health check

        # Collect alerts and determine overall status
        alerts = []
        status = HealthStatus.HEALTHY
        recommendations = []

        # Check LLM metrics against thresholds
        if llm_available:
            if llm_success_rate < ALERTING_THRESHOLDS['llm_success_rate']['critical']:
                status = HealthStatus.UNHEALTHY
                alerts.append(f"LLM success rate critical: {llm_success_rate:.1%} < {ALERTING_THRESHOLDS['llm_success_rate']['critical']:.1%}")
                recommendations.append("Check LLM service status and logs")
                recommendations.append("Run: obra logs --level=ERROR --since='10m'")
            elif llm_success_rate < ALERTING_THRESHOLDS['llm_success_rate']['warning']:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                alerts.append(f"LLM success rate low: {llm_success_rate:.1%} < {ALERTING_THRESHOLDS['llm_success_rate']['warning']:.1%}")
                recommendations.append("Monitor LLM service for issues")

            if llm_latency_p95 > ALERTING_THRESHOLDS['llm_latency_p95']['critical']:
                status = HealthStatus.UNHEALTHY
                alerts.append(f"LLM latency critical: {llm_latency_p95:.0f}ms > {ALERTING_THRESHOLDS['llm_latency_p95']['critical']}ms")
                recommendations.append("LLM service overloaded - consider scaling or caching")
            elif llm_latency_p95 > ALERTING_THRESHOLDS['llm_latency_p95']['warning']:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                alerts.append(f"LLM latency elevated: {llm_latency_p95:.0f}ms > {ALERTING_THRESHOLDS['llm_latency_p95']['warning']}ms")
                recommendations.append("Monitor LLM service load")

        # Check agent metrics
        if agent_available:
            if agent_success_rate < ALERTING_THRESHOLDS['agent_success_rate']['critical']:
                status = HealthStatus.UNHEALTHY
                alerts.append(f"Agent success rate critical: {agent_success_rate:.1%} < {ALERTING_THRESHOLDS['agent_success_rate']['critical']:.1%}")
                recommendations.append("Check agent communication logs")
            elif agent_success_rate < ALERTING_THRESHOLDS['agent_success_rate']['warning']:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                alerts.append(f"Agent success rate low: {agent_success_rate:.1%} < {ALERTING_THRESHOLDS['agent_success_rate']['warning']:.1%}")

        return {
            'status': status.value,
            'alerts': alerts,
            'llm': {
                'available': llm_available,
                'success_rate': llm_success_rate,
                'latency_p95': llm_latency_p95,
                'request_count': llm_metrics['count']
            },
            'agent': {
                'available': agent_available,
                'success_rate': agent_success_rate,
                'execution_count': agent_metrics['count']
            },
            'database': {
                'available': database_available
            },
            'recommendations': recommendations,
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics and health status
        """
        return {
            'health': self.get_health_status(),
            'llm': self.get_llm_metrics(),
            'agent': self.get_agent_metrics(),
            'nl_commands': self.get_nl_command_metrics(),
            'totals': {
                'llm_requests': self.total_llm_requests,
                'agent_executions': self.total_agent_executions,
                'nl_commands': self.total_nl_commands
            },
            'window_minutes': self.window_minutes
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None
_metrics_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector.

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector

    if _metrics_collector is None:
        with _metrics_lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector(window_minutes=5)

    return _metrics_collector


def reset_metrics_collector():
    """Reset global metrics collector (for testing)."""
    global _metrics_collector

    with _metrics_lock:
        _metrics_collector = None
