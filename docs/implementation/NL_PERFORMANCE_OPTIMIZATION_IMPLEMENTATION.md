# NL Performance Optimization - Implementation Guide (Machine-Optimized)

**Target**: Claude Code Implementer
**Goal**: Reduce NL command latency from 6.3s to <500ms (12.6x improvement)
**Effort**: Phase 1 (2 hours) + Phase 2 (4 hours) = 6 hours total
**Priority**: HIGH

---

## PHASE 1: IMMEDIATE WINS (2 hours, 60x improvement for 50% traffic)

### Task 1.1: Add Metrics Recording (30 min)

**Objective**: Integrate existing metrics system into NL pipeline

#### File 1: `src/nl/intent_classifier.py`

**Add import**:
```python
from src.core.metrics import get_metrics_collector
import time
```

**Modify `classify()` method** (around line 50):
```python
def classify(self, user_input: str, context: Optional[Dict] = None) -> IntentResult:
    """Classify user input as COMMAND or QUESTION."""
    metrics = get_metrics_collector()
    start = time.time()

    # ... existing classification logic ...

    # Record metrics BEFORE return
    latency_ms = (time.time() - start) * 1000
    metrics.record_llm_request(
        provider='ollama',
        latency_ms=latency_ms,
        success=True,
        model=self.llm_plugin.model if hasattr(self.llm_plugin, 'model') else 'unknown'
    )

    return result
```

#### File 2: `src/nl/operation_classifier.py`

**Same pattern as above** - add metrics recording to `classify()` method.

#### File 3: `src/nl/entity_type_classifier.py`

**Same pattern** - add metrics recording to `classify()` method.

#### File 4: `src/nl/entity_identifier_extractor.py`

**Same pattern** - add metrics recording to `extract()` method.

#### File 5: `src/nl/parameter_extractor.py`

**Same pattern** - add metrics recording to `extract()` method.

#### File 6: `src/nl/nl_command_processor.py`

**Add import**:
```python
from src.core.metrics import get_metrics_collector
import time
```

**Modify `process()` method** (around line 180):
```python
def process(self, user_input: str, context: Optional[Dict] = None) -> ParsedIntent:
    """Process NL command through pipeline."""
    metrics = get_metrics_collector()
    start = time.time()

    # ... existing pipeline logic ...

    # Record total NL command latency BEFORE return
    latency_ms = (time.time() - start) * 1000
    operation_type = parsed_intent.operation_context.operation.value if parsed_intent.operation_context else 'unknown'
    metrics.record_nl_command(
        operation=operation_type,
        latency_ms=latency_ms,
        success=True
    )

    return parsed_intent
```

**Verification**:
```bash
# Run interactive mode, execute a command, check metrics
python -m src.cli interactive
> list all projects
> exit

# Verify metrics were recorded (add debug logging temporarily)
```

---

### Task 1.2: Implement Fast Path Matcher (1 hour)

**Objective**: 126x faster for common queries (50% of traffic)

#### File 1: `src/nl/fast_path_matcher.py` (NEW FILE)

```python
"""Fast path matcher for common NL queries.

Bypasses LLM pipeline for 50%+ of common queries using regex patterns.
Achieves 126x speedup (6.3s → 50ms) for matched queries.

Usage:
    >>> matcher = FastPathMatcher()
    >>> result = matcher.match("list all projects")
    >>> if result:
    ...     print(f"Fast path: {result.entity_type}")
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

from src.nl.types import OperationContext, OperationType, EntityType, QueryType

logger = logging.getLogger(__name__)


@dataclass
class FastPathPattern:
    """Pattern definition for fast path matching."""
    pattern: str  # Regex pattern
    operation: OperationType
    entity_type: EntityType
    query_type: Optional[QueryType] = None
    extract_id: bool = False  # Extract entity ID from pattern


class FastPathMatcher:
    """Match common queries without LLM processing.

    Covers ~50% of typical NL queries:
    - "list all projects" → QUERY PROJECT
    - "show tasks" → QUERY TASK
    - "get epic 5" → QUERY EPIC (id=5)

    Attributes:
        patterns: List of (regex, operation, entity_type) tuples
        hit_count: Number of successful matches (metrics)
        miss_count: Number of misses (metrics)
    """

    def __init__(self):
        """Initialize fast path matcher with common patterns."""
        self.patterns = [
            # Projects
            FastPathPattern(
                pattern=r"^(?:list|show|get|display)\s+(?:all\s+)?projects?$",
                operation=OperationType.QUERY,
                entity_type=EntityType.PROJECT,
                query_type=QueryType.SIMPLE
            ),
            FastPathPattern(
                pattern=r"^(?:get|show|display)\s+project\s+(\d+)$",
                operation=OperationType.QUERY,
                entity_type=EntityType.PROJECT,
                query_type=QueryType.SIMPLE,
                extract_id=True
            ),
            FastPathPattern(
                pattern=r"^(?:list|show)\s+(?:active|open)\s+projects?$",
                operation=OperationType.QUERY,
                entity_type=EntityType.PROJECT,
                query_type=QueryType.SIMPLE
            ),

            # Tasks
            FastPathPattern(
                pattern=r"^(?:list|show|get|display)\s+(?:all\s+)?tasks?$",
                operation=OperationType.QUERY,
                entity_type=EntityType.TASK,
                query_type=QueryType.SIMPLE
            ),
            FastPathPattern(
                pattern=r"^(?:show|list)\s+(?:open|pending|active)\s+tasks?$",
                operation=OperationType.QUERY,
                entity_type=EntityType.TASK,
                query_type=QueryType.SIMPLE
            ),
            FastPathPattern(
                pattern=r"^(?:get|show|display)\s+task\s+(\d+)$",
                operation=OperationType.QUERY,
                entity_type=EntityType.TASK,
                query_type=QueryType.SIMPLE,
                extract_id=True
            ),

            # Epics
            FastPathPattern(
                pattern=r"^(?:list|show|get|display)\s+(?:all\s+)?epics?$",
                operation=OperationType.QUERY,
                entity_type=EntityType.EPIC,
                query_type=QueryType.SIMPLE
            ),
            FastPathPattern(
                pattern=r"^(?:get|show|display)\s+epic\s+(\d+)$",
                operation=OperationType.QUERY,
                entity_type=EntityType.EPIC,
                query_type=QueryType.SIMPLE,
                extract_id=True
            ),

            # Stories
            FastPathPattern(
                pattern=r"^(?:list|show|get|display)\s+(?:all\s+)?stor(?:y|ies)$",
                operation=OperationType.QUERY,
                entity_type=EntityType.STORY,
                query_type=QueryType.SIMPLE
            ),
            FastPathPattern(
                pattern=r"^(?:get|show|display)\s+story\s+(\d+)$",
                operation=OperationType.QUERY,
                entity_type=EntityType.STORY,
                query_type=QueryType.SIMPLE,
                extract_id=True
            ),

            # Milestones
            FastPathPattern(
                pattern=r"^(?:list|show|get|display)\s+(?:all\s+)?milestones?$",
                operation=OperationType.QUERY,
                entity_type=EntityType.MILESTONE,
                query_type=QueryType.SIMPLE
            ),
            FastPathPattern(
                pattern=r"^(?:get|show|display)\s+milestone\s+(\d+)$",
                operation=OperationType.QUERY,
                entity_type=EntityType.MILESTONE,
                query_type=QueryType.SIMPLE,
                extract_id=True
            ),
        ]

        # Metrics
        self.hit_count = 0
        self.miss_count = 0

    def match(self, user_input: str) -> Optional[OperationContext]:
        """Match user input against fast path patterns.

        Args:
            user_input: Raw user input string

        Returns:
            OperationContext if matched, None otherwise

        Example:
            >>> matcher = FastPathMatcher()
            >>> result = matcher.match("list all projects")
            >>> assert result.operation == OperationType.QUERY
            >>> assert result.entity_type == EntityType.PROJECT
        """
        # Normalize input
        normalized = user_input.lower().strip()

        # Try each pattern
        for pattern_def in self.patterns:
            match = re.match(pattern_def.pattern, normalized, re.IGNORECASE)
            if match:
                # Extract entity ID if pattern captures it
                identifier = None
                if pattern_def.extract_id and match.groups():
                    identifier = int(match.group(1))

                # Build OperationContext
                context = OperationContext(
                    operation=pattern_def.operation,
                    entity_type=pattern_def.entity_type,
                    identifier=identifier,
                    parameters={},
                    confidence=1.0,  # Rule-based = 100% confidence
                    raw_input=user_input,
                    query_type=pattern_def.query_type
                )

                self.hit_count += 1
                logger.info(f"Fast path HIT: '{user_input}' → {pattern_def.entity_type.value}")
                return context

        # No match
        self.miss_count += 1
        logger.debug(f"Fast path MISS: '{user_input}'")
        return None

    def get_stats(self) -> dict:
        """Get fast path matching statistics.

        Returns:
            Dict with hit_count, miss_count, hit_rate
        """
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0.0

        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'total': total,
            'hit_rate': hit_rate
        }
```

#### File 2: `src/nl/nl_command_processor.py`

**Add import**:
```python
from src.nl.fast_path_matcher import FastPathMatcher
```

**Add to `__init__()` method** (around line 145):
```python
# Initialize fast path matcher
self.fast_path_matcher = FastPathMatcher()
```

**Modify `process()` method** (around line 200, BEFORE intent classification):
```python
def process(self, user_input: str, context: Optional[Dict] = None) -> ParsedIntent:
    """Process NL command through pipeline."""
    metrics = get_metrics_collector()
    start = time.time()

    # TRY FAST PATH FIRST (bypass LLM for common queries)
    fast_path_context = self.fast_path_matcher.match(user_input)
    if fast_path_context:
        logger.info(f"Fast path matched: {user_input} → {fast_path_context.entity_type.value}")

        # Build ParsedIntent from fast path result
        parsed_intent = ParsedIntent(
            intent_type='COMMAND',
            operation_context=fast_path_context,
            original_message=user_input,
            confidence=1.0,
            requires_execution=True,
            metadata={'fast_path': True}
        )

        # Record metrics
        latency_ms = (time.time() - start) * 1000
        metrics.record_nl_command(
            operation=fast_path_context.operation.value,
            latency_ms=latency_ms,
            success=True
        )

        return parsed_intent

    # Fall back to full LLM pipeline
    logger.debug(f"Fast path miss, using LLM pipeline: {user_input}")
    # ... existing intent classification logic ...
```

**Verification**:
```bash
# Test fast path
python -m src.cli interactive
> list all projects
# Should see: "Fast path matched: list all projects → project"
# Latency should be ~50ms
```

---

### Task 1.3: Enable LLM Keep-Alive (15 min)

**Objective**: Eliminate model cold start overhead (1.4x faster)

#### File: `src/llm/local_interface.py`

**Find `generate()` method** (around line 80):

**Before**:
```python
response = requests.post(
    f"{self.api_url}/api/generate",
    json={
        'model': self.model_name,
        'prompt': prompt,
        **kwargs
    }
)
```

**After**:
```python
response = requests.post(
    f"{self.api_url}/api/generate",
    json={
        'model': self.model_name,
        'prompt': prompt,
        'keep_alive': -1,  # Keep model loaded indefinitely
        **kwargs
    }
)
```

**Verification**:
```bash
# Check model stays loaded
curl http://10.0.75.1:11434/api/ps
# Should show qwen2.5-coder:32b with "expires_at": never
```

---

### Task 1.4: Add Metrics CLI Command (15 min)

**Objective**: View NL command performance metrics

#### File: `src/cli.py`

**Add metrics command group** (around line 500, after existing commands):

```python
@cli.group()
def metrics():
    """View performance metrics."""
    pass


@metrics.command(name='nl')
def metrics_nl():
    """View NL command performance metrics."""
    from src.core.metrics import get_metrics_collector

    metrics = get_metrics_collector()
    nl_metrics = metrics.get_nl_command_metrics()

    click.echo("\nNL Command Performance (last 5 minutes)")
    click.echo("=" * 60)
    click.echo(f"Total Commands:     {nl_metrics['count']}")
    click.echo(f"Success Rate:       {nl_metrics['success_rate']:.1%}")
    click.echo(f"Avg Latency:        {nl_metrics['avg_latency']:.0f}ms")
    click.echo()

    if nl_metrics['by_operation']:
        click.echo("By Operation:")
        for op, data in nl_metrics['by_operation'].items():
            click.echo(f"  {op:8s}  {data['count']:3d} commands, {data['success_rate']:.1%} success")

    click.echo()


@metrics.command(name='llm')
def metrics_llm():
    """View LLM performance metrics."""
    from src.core.metrics import get_metrics_collector

    metrics = get_metrics_collector()
    llm_metrics = metrics.get_llm_metrics()

    click.echo("\nLLM Performance (last 5 minutes)")
    click.echo("=" * 60)
    click.echo(f"Total Requests:     {llm_metrics['count']}")
    click.echo(f"Success Rate:       {llm_metrics['success_rate']:.1%}")
    click.echo(f"Avg Latency:        {llm_metrics['avg_latency']:.0f}ms")
    click.echo(f"P50 Latency:        {llm_metrics['latency_p50']:.0f}ms")
    click.echo(f"P95 Latency:        {llm_metrics['latency_p95']:.0f}ms")
    click.echo(f"P99 Latency:        {llm_metrics['latency_p99']:.0f}ms")
    click.echo()

    if llm_metrics['by_provider']:
        click.echo("By Provider:")
        for provider, data in llm_metrics['by_provider'].items():
            click.echo(f"  {provider:12s}  {data['count']:3d} requests, {data['success_rate']:.1%} success")

    click.echo()


@metrics.command(name='health')
def metrics_health():
    """View system health status."""
    from src.core.metrics import get_metrics_collector

    metrics = get_metrics_collector()
    health = metrics.get_health_status()

    # Color-code status
    status_color = {
        'healthy': 'green',
        'degraded': 'yellow',
        'unhealthy': 'red'
    }.get(health['status'], 'white')

    click.echo("\nSystem Health")
    click.echo("=" * 60)
    click.secho(f"Status: {health['status'].upper()}", fg=status_color, bold=True)
    click.echo()

    if health['alerts']:
        click.echo("Alerts:")
        for alert in health['alerts']:
            click.secho(f"  ⚠️  {alert}", fg='yellow')
        click.echo()

    click.echo("Components:")
    click.echo(f"  LLM:       {'✓' if health['llm']['available'] else '✗'} "
               f"({health['llm']['success_rate']:.1%} success, "
               f"{health['llm']['latency_p95']:.0f}ms P95)")
    click.echo(f"  Agent:     {'✓' if health['agent']['available'] else '✗'} "
               f"({health['agent']['success_rate']:.1%} success)")
    click.echo(f"  Database:  {'✓' if health['database']['available'] else '✗'}")
    click.echo()

    if health['recommendations']:
        click.echo("Recommendations:")
        for rec in health['recommendations']:
            click.echo(f"  • {rec}")
        click.echo()
```

**Verification**:
```bash
# Test metrics commands
python -m src.cli metrics nl
python -m src.cli metrics llm
python -m src.cli metrics health
```

---

## PHASE 2: MEDIUM WINS (4 hours, 12x additional improvement)

### Task 2.1: Implement Query Response Caching (2 hours)

**Objective**: 630x faster for repeated queries (30% of traffic)

#### File 1: `src/nl/query_cache.py` (NEW FILE)

```python
"""Query response caching for NL commands.

Caches QUERY operation results to avoid redundant LLM processing.
Achieves 630x speedup (6.3s → 10ms) for cache hits.

Usage:
    >>> cache = QueryCache(ttl_seconds=60)
    >>> result = cache.get("list all projects", context={})
    >>> if not result:
    ...     result = expensive_query()
    ...     cache.put("list all projects", context={}, result=result)
"""

import time
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class CachedResult:
    """Cached query result with metadata."""
    result: Any
    timestamp: float
    hit_count: int = 0


class QueryCache:
    """LRU cache for NL query results with TTL.

    Caches only QUERY operations (not CREATE/UPDATE/DELETE).
    Uses normalized input + context as cache key.

    Attributes:
        ttl_seconds: Time-to-live for cache entries
        max_entries: Maximum cache size (LRU eviction)
        cache: OrderedDict for LRU behavior
        hit_count: Cache hits (metrics)
        miss_count: Cache misses (metrics)
    """

    def __init__(self, ttl_seconds: int = 60, max_entries: int = 1000):
        """Initialize query cache.

        Args:
            ttl_seconds: Cache entry TTL (default: 60s)
            max_entries: Max cache size (default: 1000)
        """
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.cache: OrderedDict[str, CachedResult] = OrderedDict()

        # Metrics
        self.hit_count = 0
        self.miss_count = 0

    def _generate_cache_key(self, user_input: str, context: Dict[str, Any]) -> str:
        """Generate cache key from normalized input + context.

        Args:
            user_input: User's query string
            context: Query context (project_id, filters, etc.)

        Returns:
            MD5 hash of normalized input + context
        """
        # Normalize input (lowercase, strip whitespace, remove articles)
        normalized = user_input.lower().strip()
        normalized = normalized.replace(' the ', ' ').replace(' a ', ' ').replace(' an ', ' ')

        # Serialize context (sorted keys for consistency)
        context_str = json.dumps(context, sort_keys=True) if context else '{}'

        # Hash for cache key
        key_str = f"{normalized}:{context_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, user_input: str, context: Optional[Dict] = None) -> Optional[Any]:
        """Get cached result if fresh.

        Args:
            user_input: User's query string
            context: Query context

        Returns:
            Cached result if fresh, None if miss/expired
        """
        key = self._generate_cache_key(user_input, context or {})

        # Check cache
        if key in self.cache:
            cached = self.cache[key]
            age = time.time() - cached.timestamp

            # Check TTL
            if age < self.ttl_seconds:
                # Move to end (LRU)
                self.cache.move_to_end(key)
                cached.hit_count += 1
                self.hit_count += 1

                logger.info(f"Cache HIT: '{user_input}' (age={age:.1f}s, hits={cached.hit_count})")
                return cached.result
            else:
                # Expired - remove
                del self.cache[key]
                logger.debug(f"Cache EXPIRED: '{user_input}' (age={age:.1f}s)")

        # Cache miss
        self.miss_count += 1
        logger.debug(f"Cache MISS: '{user_input}'")
        return None

    def put(self, user_input: str, context: Optional[Dict], result: Any):
        """Cache query result.

        Args:
            user_input: User's query string
            context: Query context
            result: Query result to cache
        """
        key = self._generate_cache_key(user_input, context or {})

        # Add to cache
        self.cache[key] = CachedResult(
            result=result,
            timestamp=time.time(),
            hit_count=0
        )

        # Move to end (most recent)
        self.cache.move_to_end(key)

        # Evict if over limit (LRU)
        if len(self.cache) > self.max_entries:
            oldest_key = next(iter(self.cache))
            evicted = self.cache.pop(oldest_key)
            logger.debug(f"Cache EVICTED: {oldest_key} (hits={evicted.hit_count})")

        logger.debug(f"Cache PUT: '{user_input}' (cache_size={len(self.cache)})")

    def clear(self):
        """Clear entire cache."""
        self.cache.clear()
        logger.info("Cache CLEARED")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hit_count, miss_count, hit_rate, size, etc.
        """
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0.0

        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'total_requests': total,
            'hit_rate': hit_rate,
            'cache_size': len(self.cache),
            'max_entries': self.max_entries,
            'ttl_seconds': self.ttl_seconds
        }
```

#### File 2: `src/nl/nl_command_processor.py`

**Add import**:
```python
from src.nl.query_cache import QueryCache
```

**Add to `__init__()` method**:
```python
# Initialize query cache
self.query_cache = QueryCache(
    ttl_seconds=config.get('nl_commands.query_cache.ttl_seconds', 60),
    max_entries=config.get('nl_commands.query_cache.max_entries', 1000)
)
```

**Modify `process()` method** (AFTER fast path check):
```python
def process(self, user_input: str, context: Optional[Dict] = None) -> ParsedIntent:
    """Process NL command through pipeline."""
    metrics = get_metrics_collector()
    start = time.time()

    # Try fast path first
    fast_path_context = self.fast_path_matcher.match(user_input)
    if fast_path_context:
        # ... fast path logic ...

    # CHECK CACHE (before LLM pipeline)
    cached_result = self.query_cache.get(user_input, context)
    if cached_result:
        logger.info(f"Cache hit: {user_input}")

        # Record metrics
        latency_ms = (time.time() - start) * 1000
        metrics.record_nl_command(
            operation='QUERY',
            latency_ms=latency_ms,
            success=True
        )

        return cached_result

    # Run full LLM pipeline
    parsed_intent = self._process_with_llm(user_input, context)

    # CACHE RESULT (only for QUERY operations)
    if (parsed_intent.operation_context and
        parsed_intent.operation_context.operation == OperationType.QUERY):
        self.query_cache.put(user_input, context, parsed_intent)

    # Record metrics
    latency_ms = (time.time() - start) * 1000
    metrics.record_nl_command(
        operation=parsed_intent.operation_context.operation.value,
        latency_ms=latency_ms,
        success=True
    )

    return parsed_intent
```

**Verification**:
```bash
# Test cache
python -m src.cli interactive
> list all projects
# First time: slow (~6s)
> list all projects
# Second time: fast (~10ms)
```

---

### Task 2.2: Optimize LLM Prompts (2 hours)

**Objective**: Reduce token count by 60% (1.5x faster)

#### Pattern: Replace verbose prompts with concise structured prompts

**Apply to ALL classifiers**: `intent_classifier.py`, `operation_classifier.py`, `entity_type_classifier.py`, `entity_identifier_extractor.py`, `parameter_extractor.py`

**Before (verbose - 250 tokens)**:
```python
prompt = f"""
You are a command intent classifier for the Obra orchestration system.

Your task is to classify user input into one of two categories:
1. COMMAND - The user wants to execute an action (create, update, delete, query)
2. QUESTION - The user wants information or help

Examples of COMMAND intents:
- "Create epic for authentication" → COMMAND
- "Update task 5 to completed" → COMMAND
- "Delete project 3" → COMMAND

Examples of QUESTION intents:
- "What is an epic?" → QUESTION
- "How do I create a task?" → QUESTION

User input: {user_input}

Respond ONLY with valid JSON in this exact format:
{{"intent": "COMMAND", "confidence": 0.95}}
"""
```

**After (concise - 45 tokens)**:
```python
prompt = f"""Classify intent (COMMAND or QUESTION):
Input: {user_input}
JSON: {{"intent": "", "confidence": 0.0}}"""
```

**Apply to each classifier** with domain-specific prompts.

---

### Task 2.3: Tune LLM Generation Parameters (1 hour)

**Objective**: 2x faster by reducing token generation

#### File: All NL classifiers

**Find all `llm_plugin.generate()` calls** and add parameters:

**Before**:
```python
response = self.llm_plugin.generate(prompt)
```

**After**:
```python
response = self.llm_plugin.generate(
    prompt,
    max_tokens=50,        # Classification needs 10-50 tokens (was: 200)
    temperature=0.1,      # Lower = faster, more deterministic (was: 0.7)
    top_p=0.9,           # Faster sampling (was: 0.95)
    stop=["\n", "}"]     # Stop early on JSON completion
)
```

---

## TESTING REQUIREMENTS

### Unit Tests (Required)

Create `tests/nl/test_fast_path_matcher.py`:
```python
def test_fast_path_list_projects():
    """Fast path matches 'list all projects'."""
    matcher = FastPathMatcher()
    result = matcher.match("list all projects")
    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.PROJECT
    assert result.confidence == 1.0

def test_fast_path_case_insensitive():
    """Fast path is case-insensitive."""
    matcher = FastPathMatcher()
    assert matcher.match("LIST ALL PROJECTS") is not None
    assert matcher.match("list all projects") is not None
    assert matcher.match("List All Projects") is not None

# Add 18 more tests for all patterns
```

Create `tests/nl/test_query_cache.py`:
```python
def test_cache_hit():
    """Cache returns result on second call."""
    cache = QueryCache(ttl_seconds=60)

    # First call - miss
    result1 = cache.get("list projects", {})
    assert result1 is None

    # Put result
    cache.put("list projects", {}, "cached_data")

    # Second call - hit
    result2 = cache.get("list projects", {})
    assert result2 == "cached_data"

def test_cache_ttl_expiration():
    """Cache expires after TTL."""
    cache = QueryCache(ttl_seconds=1)
    cache.put("test", {}, "data")

    time.sleep(1.1)

    result = cache.get("test", {})
    assert result is None  # Expired

# Add 13 more tests for TTL, eviction, normalization
```

### Integration Tests (Required)

Create `tests/integration/test_nl_performance.py`:
```python
def test_fast_path_latency(real_nl_processor):
    """Fast path completes in <100ms."""
    start = time.time()
    result = real_nl_processor.process("list all projects")
    latency = (time.time() - start) * 1000

    assert latency < 100  # <100ms for fast path
    assert result.metadata.get('fast_path') is True

def test_cache_hit_latency(real_nl_processor):
    """Cache hit completes in <20ms."""
    # Prime cache
    real_nl_processor.process("list all projects")

    # Measure cache hit
    start = time.time()
    result = real_nl_processor.process("list all projects")
    latency = (time.time() - start) * 1000

    assert latency < 20  # <20ms for cache hit
```

---

## VERIFICATION CHECKLIST

### Phase 1 Complete
- [ ] Metrics recording added to all 5 classifiers
- [ ] Metrics recording added to NLCommandProcessor
- [ ] Fast path matcher implemented (20 patterns)
- [ ] Fast path integrated into NLCommandProcessor
- [ ] LLM keep-alive enabled
- [ ] Metrics CLI commands added (nl, llm, health)
- [ ] Unit tests passing (20+ tests)
- [ ] "list all projects" completes in <100ms
- [ ] Fast path hit rate >50%

### Phase 2 Complete
- [ ] Query cache implemented
- [ ] Query cache integrated into NLCommandProcessor
- [ ] LLM prompts optimized (all 5 classifiers)
- [ ] LLM generation parameters tuned
- [ ] Unit tests passing (35+ tests)
- [ ] Cache hit rate >30%
- [ ] Average latency <500ms
- [ ] P95 latency <1,500ms

---

## SUCCESS METRICS

| Metric | Baseline | Phase 1 | Phase 2 | Target |
|--------|----------|---------|---------|--------|
| Avg Latency | 6,300ms | 2,400ms | 450ms | <1,000ms |
| P50 Latency | 6,200ms | 50ms | 10ms | <500ms |
| P95 Latency | 7,500ms | 4,500ms | 1,200ms | <1,500ms |
| Fast Path Rate | 0% | 50% | 55% | >50% |
| Cache Hit Rate | 0% | 0% | 35% | >30% |

---

**EXECUTION ORDER**: Tasks must be completed sequentially within each phase. Phase 2 depends on Phase 1 completion.

**ESTIMATED EFFORT**: 6 hours total (2h Phase 1 + 4h Phase 2)

**VALIDATION**: Run `python -m pytest tests/nl/` after each task. Run interactive mode and execute "list all projects" to verify latency.
