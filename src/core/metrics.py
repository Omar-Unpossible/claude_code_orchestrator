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
import threading


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

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status.

        Returns:
            Dictionary with health status:
            - status: 'healthy' | 'degraded' | 'unhealthy'
            - llm_available: bool
            - llm_success_rate: float (0-1)
            - llm_latency_p95: float (ms)
            - agent_available: bool
            - agent_success_rate: float (0-1)
            - database_available: bool
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

        # Overall status
        status = 'healthy'

        # Degrade if success rates drop
        if llm_available and llm_success_rate < 0.95:
            status = 'degraded'

        if agent_available and agent_success_rate < 0.90:
            status = 'degraded'

        # Degrade if latency too high
        if llm_latency_p95 > 5000:  # 5 seconds
            status = 'degraded'

        # Unhealthy if critical components down
        if llm_available and llm_success_rate < 0.80:
            status = 'unhealthy'

        if agent_available and agent_success_rate < 0.70:
            status = 'unhealthy'

        return {
            'status': status,
            'llm_available': llm_available,
            'llm_success_rate': llm_success_rate,
            'llm_latency_p95': llm_latency_p95,
            'agent_available': agent_available,
            'agent_success_rate': agent_success_rate,
            'database_available': database_available,
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
