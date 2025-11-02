"""Tests for ContextManager - context prioritization and summarization."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock

from src.core.models import Task
from src.utils.token_counter import TokenCounter
from src.utils.context_manager import ContextManager


@pytest.fixture
def token_counter():
    """Create TokenCounter instance."""
    return TokenCounter()


@pytest.fixture
def manager(token_counter):
    """Create ContextManager instance."""
    return ContextManager(token_counter)


@pytest.fixture
def llm_interface():
    """Create mock LLM interface."""
    mock_llm = Mock()
    mock_llm.send_prompt = Mock(return_value="This is a summary.")
    return mock_llm


@pytest.fixture
def task():
    """Create test task."""
    task = Mock(spec=Task)
    task.id = 1
    task.project_id = 1
    task.description = "Implement a function to add two numbers"
    return task


class TestContextManagerInitialization:
    """Test ContextManager initialization."""

    def test_default_initialization(self, token_counter):
        """Test manager initializes with defaults."""
        manager = ContextManager(token_counter)

        assert manager.token_counter is token_counter
        assert manager.llm_interface is None
        assert manager._max_tokens == 100000
        assert len(manager._context_items) == 0

    def test_custom_config_initialization(self, token_counter):
        """Test manager initializes with custom config."""
        config = {
            'max_tokens': 50000,
            'summarization_threshold': 25000,
            'compression_ratio': 0.5
        }
        manager = ContextManager(token_counter, config=config)

        assert manager._max_tokens == 50000
        assert manager._summarization_threshold == 25000
        assert manager._compression_ratio == 0.5


class TestContextBuilding:
    """Test context building functionality."""

    def test_build_context_basic(self, manager):
        """Test building basic context."""
        items = [
            {'type': 'task', 'content': 'Implement feature X', 'priority': 10},
            {'type': 'code', 'content': 'def foo(): pass', 'priority': 8}
        ]

        context = manager.build_context(items, max_tokens=1000)

        assert isinstance(context, str)
        assert 'Implement feature X' in context
        assert 'def foo(): pass' in context

    def test_build_context_empty_items(self, manager):
        """Test building context with no items."""
        context = manager.build_context([], max_tokens=1000)

        assert context == ""

    def test_build_context_respects_token_limit(self, manager):
        """Test context stays within token limit."""
        items = [
            {'type': 'text', 'content': 'word ' * 1000, 'priority': 10}
        ]

        context = manager.build_context(items, max_tokens=100)
        token_count = manager.token_counter.count_tokens(context)

        # Should be at or under limit
        assert token_count <= 150  # Some margin for summarization markers

    def test_build_context_prioritization(self, manager):
        """Test high priority items included first."""
        items = [
            {'type': 'low', 'content': 'Low priority text ' * 100, 'priority': 1},
            {'type': 'high', 'content': 'High priority', 'priority': 10}
        ]

        context = manager.build_context(items, max_tokens=50)

        # High priority should be included
        assert 'High priority' in context

    def test_build_context_caching(self, manager):
        """Test context building uses cache."""
        items = [{'type': 'task', 'content': 'Test', 'priority': 5}]

        context1 = manager.build_context(items, max_tokens=1000)
        context2 = manager.build_context(items, max_tokens=1000)

        assert context1 == context2
        assert len(manager._context_cache) > 0


class TestPrioritization:
    """Test context item prioritization."""

    def test_prioritize_context_basic(self, manager):
        """Test basic prioritization."""
        items = [
            {'type': 'code', 'content': 'def foo(): pass', 'priority': 5},
            {'type': 'task', 'content': 'Important task', 'priority': 10}
        ]

        prioritized = manager.prioritize_context(items)

        assert len(prioritized) == 2
        # Higher priority should come first
        assert prioritized[0][0]['priority'] >= prioritized[1][0]['priority']

    def test_prioritize_with_recency(self, manager):
        """Test prioritization considers recency."""
        now = datetime.now(UTC)
        old = now - timedelta(days=10)

        items = [
            {'type': 'old', 'content': 'Old content', 'priority': 5, 'timestamp': old},
            {'type': 'new', 'content': 'New content', 'priority': 5, 'timestamp': now}
        ]

        prioritized = manager.prioritize_context(items)

        # Recent item should score higher
        scores = [score for _, score in prioritized]
        assert scores[0] > scores[1]

    def test_prioritize_with_task_relevance(self, manager, task):
        """Test prioritization considers task relevance."""
        items = [
            {'type': 'relevant', 'content': 'Implement function add numbers', 'priority': 5},
            {'type': 'irrelevant', 'content': 'Unrelated content xyz', 'priority': 5}
        ]

        prioritized = manager.prioritize_context(items, task=task)

        # Relevant item should score higher
        assert prioritized[0][0]['type'] == 'relevant'


class TestSummarization:
    """Test context summarization."""

    def test_summarize_context_with_llm(self, token_counter, llm_interface):
        """Test summarization using LLM."""
        manager = ContextManager(token_counter, llm_interface=llm_interface)

        text = "Long text " * 100
        summary = manager.summarize_context(text, target_tokens=50)

        assert llm_interface.send_prompt.called
        assert len(summary) < len(text)

    def test_summarize_context_fallback(self, manager):
        """Test summarization falls back without LLM."""
        text = "First sentence. Middle sentence. Last sentence."
        summary = manager.summarize_context(text, target_tokens=20)

        # Should use extractive summarization
        assert 'First sentence' in summary
        assert len(summary) < len(text)

    def test_extractive_summary(self, manager):
        """Test extractive summarization."""
        text = "First. Second. Third. Fourth. Fifth."
        summary = manager._extractive_summary(text, target_tokens=10)

        # Should include first and last
        assert 'First' in summary
        assert 'Fifth' in summary


class TestCompression:
    """Test context compression."""

    def test_compress_context(self, manager):
        """Test compressing context."""
        text = "Long text " * 100
        compressed = manager.compress_context(text, compression_ratio=0.5)

        original_tokens = manager.token_counter.count_tokens(text)
        compressed_tokens = manager.token_counter.count_tokens(compressed)

        # Should be smaller or equal (for very short text, may be similar)
        assert compressed_tokens <= original_tokens


class TestContextStorage:
    """Test context storage operations."""

    def test_add_to_context(self, manager):
        """Test adding items to context storage."""
        manager.add_to_context({'type': 'note', 'content': 'Test note'}, priority=8)

        assert len(manager._context_items) == 1
        assert manager._context_items[0]['priority'] == 8
        assert 'timestamp' in manager._context_items[0]

    def test_clear_context(self, manager):
        """Test clearing context."""
        manager.add_to_context({'type': 'note', 'content': 'Test'})
        manager.clear_context()

        assert len(manager._context_items) == 0
        assert len(manager._context_cache) == 0

    def test_update_context(self, manager):
        """Test updating context."""
        updates = {'new_data': 'value', 'another': 'item'}
        manager.update_context(updates)

        assert len(manager._context_items) == 2


class TestContextSearch:
    """Test context search functionality."""

    def test_search_context_basic(self, manager):
        """Test basic context search."""
        manager.add_to_context({'type': 'code', 'content': 'Python implementation'})
        manager.add_to_context({'type': 'note', 'content': 'Java documentation'})

        results = manager.search_context('Python', top_k=5)

        assert len(results) == 1
        assert 'Python implementation' in results

    def test_search_context_top_k(self, manager):
        """Test search returns top K results."""
        for i in range(10):
            manager.add_to_context({'type': 'item', 'content': f'Python code {i}'})

        results = manager.search_context('Python', top_k=3)

        assert len(results) == 3

    def test_search_context_no_matches(self, manager):
        """Test search with no matches."""
        manager.add_to_context({'type': 'note', 'content': 'Unrelated content'})

        results = manager.search_context('nonexistent', top_k=5)

        assert len(results) == 0


class TestRelevantContext:
    """Test getting relevant context for tasks."""

    def test_get_relevant_context(self, manager, task):
        """Test getting relevant context for task."""
        manager.add_to_context({'type': 'code', 'content': 'def add(a, b): return a + b'})
        manager.add_to_context({'type': 'task', 'content': 'Implement addition'})

        context = manager.get_relevant_context(task, max_tokens=1000)

        assert isinstance(context, str)
        assert len(context) > 0


class TestStatistics:
    """Test statistics and monitoring."""

    def test_get_stats(self, manager):
        """Test getting context manager statistics."""
        manager.add_to_context({'type': 'item', 'content': 'Test'})

        stats = manager.get_stats()

        assert 'total_items' in stats
        assert 'cache_size' in stats
        assert 'max_tokens' in stats
        assert stats['total_items'] == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_content_items(self, manager):
        """Test handling items with empty content."""
        items = [
            {'type': 'empty', 'content': '', 'priority': 5}
        ]

        context = manager.build_context(items, max_tokens=1000)

        # Should handle gracefully
        assert isinstance(context, str)

    def test_very_large_context(self, manager):
        """Test handling very large context."""
        items = [
            {'type': 'large', 'content': 'word ' * 100000, 'priority': 5}
        ]

        context = manager.build_context(items, max_tokens=100)

        # Should truncate/summarize
        token_count = manager.token_counter.count_tokens(context)
        assert token_count <= 150  # Within limit with margin

    def test_missing_priority(self, manager):
        """Test items without explicit priority."""
        items = [
            {'type': 'task', 'content': 'No priority set'}
        ]

        prioritized = manager.prioritize_context(items)

        # Should still work with default priority
        assert len(prioritized) == 1

    def test_invalid_timestamp(self, manager):
        """Test handling invalid timestamp."""
        items = [
            {'type': 'item', 'content': 'Test', 'timestamp': 'invalid'}
        ]

        # Should not crash
        prioritized = manager.prioritize_context(items)
        assert len(prioritized) == 1


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_add_to_context(self, manager):
        """Test adding to context concurrently."""
        import threading

        def add_items():
            for i in range(10):
                manager.add_to_context({'type': 'item', 'content': f'Item {i}'})

        threads = [threading.Thread(target=add_items) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Should have all items
        assert len(manager._context_items) == 30

    def test_concurrent_build_context(self, manager):
        """Test building context concurrently."""
        import threading

        items = [{'type': 'item', 'content': f'Item {i}'} for i in range(10)]
        results = []

        def build():
            context = manager.build_context(items, max_tokens=1000)
            results.append(context)

        threads = [threading.Thread(target=build) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # All should complete
        assert len(results) == 5
