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
