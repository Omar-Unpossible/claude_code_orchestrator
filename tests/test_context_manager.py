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


class TestTemplateSpecificPriorities:
    """Test template-specific context priorities (TASK_1.1)."""

    def test_priority_by_template_exists(self, manager):
        """Test that PRIORITY_BY_TEMPLATE constant exists."""
        assert hasattr(ContextManager, 'PRIORITY_BY_TEMPLATE')
        assert isinstance(ContextManager.PRIORITY_BY_TEMPLATE, dict)
        assert 'validation' in ContextManager.PRIORITY_BY_TEMPLATE
        assert 'task_execution' in ContextManager.PRIORITY_BY_TEMPLATE
        assert 'error_analysis' in ContextManager.PRIORITY_BY_TEMPLATE

    def test_build_context_accepts_template_name(self, manager):
        """Test that build_context accepts template_name parameter."""
        items = [{'type': 'current_task_description', 'content': 'Test task', 'priority': 5}]

        # Should not raise error
        context = manager.build_context(items, max_tokens=1000, template_name='validation')
        assert 'Test task' in context

    def test_build_context_with_unknown_template_fallback(self, manager):
        """Test that build_context falls back to default for unknown template."""
        items = [{'type': 'current_task_description', 'content': 'Test task', 'priority': 5}]

        # Unknown template should use DEFAULT_PRIORITY_ORDER
        context = manager.build_context(items, max_tokens=1000, template_name='unknown_template')
        assert 'Test task' in context

    def test_validation_template_priority_order(self, manager):
        """Test that validation template has expected priority order."""
        validation_order = ContextManager.PRIORITY_BY_TEMPLATE['validation']

        # Validation should prioritize work_output and expected_outcome
        assert 'work_output' in validation_order
        assert 'expected_outcome' in validation_order
        assert 'file_changes' in validation_order
        assert validation_order.index('work_output') < validation_order.index('task_description')

    def test_task_execution_template_priority_order(self, manager):
        """Test that task_execution template has expected priority order."""
        task_order = ContextManager.PRIORITY_BY_TEMPLATE['task_execution']

        # Task execution should prioritize task description and errors
        assert 'current_task_description' in task_order
        assert 'recent_errors' in task_order
        assert task_order[0] == 'current_task_description'

    def test_template_specific_context_building(self, manager):
        """Test that different templates affect context ordering."""
        # Create items that would be prioritized differently by templates
        items = [
            {'type': 'work_output', 'content': 'Output data', 'priority': 5},
            {'type': 'current_task_description', 'content': 'Task description', 'priority': 5},
            {'type': 'file_changes', 'content': 'File changes', 'priority': 5}
        ]

        # Build with validation template (should prioritize work_output)
        validation_context = manager.build_context(
            items, max_tokens=1000, template_name='validation'
        )

        # Build with task_execution template (should prioritize task_description)
        task_context = manager.build_context(
            items, max_tokens=1000, template_name='task_execution'
        )

        # Both should contain content, but ordering may differ
        assert 'Output data' in validation_context
        assert 'Task description' in task_context


class TestTemplateSpecificWeights:
    """Test template-specific weight tuning (TASK_3.1)."""

    def test_weights_by_template_exists(self, manager):
        """Test that WEIGHTS_BY_TEMPLATE constant exists."""
        assert hasattr(ContextManager, 'WEIGHTS_BY_TEMPLATE')
        assert isinstance(ContextManager.WEIGHTS_BY_TEMPLATE, dict)

        # Check all expected templates
        assert 'validation' in ContextManager.WEIGHTS_BY_TEMPLATE
        assert 'task_execution' in ContextManager.WEIGHTS_BY_TEMPLATE
        assert 'error_analysis' in ContextManager.WEIGHTS_BY_TEMPLATE
        assert 'decision' in ContextManager.WEIGHTS_BY_TEMPLATE
        assert 'code_review' in ContextManager.WEIGHTS_BY_TEMPLATE

    def test_weights_by_template_structure(self, manager):
        """Test that each template has correct weight structure."""
        for template_name, weights in ContextManager.WEIGHTS_BY_TEMPLATE.items():
            # Each template should have all four weight keys
            assert 'recency' in weights, f"{template_name} missing recency"
            assert 'relevance' in weights, f"{template_name} missing relevance"
            assert 'importance' in weights, f"{template_name} missing importance"
            assert 'size_efficiency' in weights, f"{template_name} missing size_efficiency"

            # Weights should sum to 1.0 (or very close)
            total = weights['recency'] + weights['relevance'] + weights['importance'] + weights['size_efficiency']
            assert 0.99 <= total <= 1.01, f"{template_name} weights sum to {total}, not 1.0"

    def test_validation_template_weights(self, manager):
        """Test validation template emphasizes importance (critical facts)."""
        weights = ContextManager.WEIGHTS_BY_TEMPLATE['validation']

        # Validation should weight importance highest (0.5)
        assert weights['importance'] == 0.5
        # Relevance moderate (0.3)
        assert weights['relevance'] == 0.3
        # Recency low (0.1) - correctness more important than recency
        assert weights['recency'] == 0.1

    def test_task_execution_template_weights(self, manager):
        """Test task_execution template emphasizes relevance (code examples)."""
        weights = ContextManager.WEIGHTS_BY_TEMPLATE['task_execution']

        # Task execution should weight relevance highest (0.5)
        assert weights['relevance'] == 0.5
        # Recency and importance balanced (0.2 each)
        assert weights['recency'] == 0.2
        assert weights['importance'] == 0.2

    def test_error_analysis_template_weights(self, manager):
        """Test error_analysis template emphasizes recency (recent errors)."""
        weights = ContextManager.WEIGHTS_BY_TEMPLATE['error_analysis']

        # Error analysis should weight recency highest (0.5)
        assert weights['recency'] == 0.5
        # Relevance and importance balanced (0.2 each)
        assert weights['relevance'] == 0.2
        assert weights['importance'] == 0.2

    def test_scoring_uses_template_weights(self, manager):
        """Test that scoring actually uses template-specific weights."""
        # Create item with high importance but low recency
        old_date = datetime.now(UTC) - timedelta(days=30)
        item = {
            'type': 'test_results',
            'content': 'Test passed successfully',
            'priority': 10,  # High importance
            'timestamp': old_date  # Low recency
        }

        priority_order = ['test_results']

        # Score with validation template (high importance weight = 0.5)
        validation_score = manager._score_context_item(item, None, priority_order, 'validation')

        # Score with error_analysis template (high recency weight = 0.5)
        error_score = manager._score_context_item(item, None, priority_order, 'error_analysis')

        # Validation should score higher (values importance over recency)
        assert validation_score > error_score

    def test_scoring_with_relevance_emphasis(self, manager, task):
        """Test that task_execution template emphasizes relevance."""
        # Create item with high relevance to task but low importance
        item = {
            'type': 'code_example',
            'content': 'function to add two numbers',  # Matches task description
            'priority': 2,  # Low importance
            'timestamp': datetime.now(UTC) - timedelta(days=10)  # Medium recency
        }

        # Don't include type in priority_order to avoid type bonus (pure importance test)
        priority_order = ['other_type']

        # Score with task_execution template (high relevance weight = 0.5)
        task_score = manager._score_context_item(item, task, priority_order, 'task_execution')

        # Score with validation template (lower relevance weight = 0.3)
        validation_score = manager._score_context_item(item, task, priority_order, 'validation')

        # Task execution should score higher (values relevance more)
        # With genuinely low importance (no type bonus) and high relevance,
        # task_execution's higher relevance weight (0.5 vs 0.3) should dominate
        assert task_score > validation_score

    def test_scoring_with_recency_emphasis(self, manager):
        """Test that error_analysis template emphasizes recency."""
        # Create very recent item with low importance
        recent_item = {
            'type': 'error_log',
            'content': 'Recent error occurred',
            'priority': 3,  # Low importance
            'timestamp': datetime.now(UTC)  # Very recent
        }

        # Create old item with high importance
        old_item = {
            'type': 'error_log',
            'content': 'Old error occurred',
            'priority': 10,  # High importance
            'timestamp': datetime.now(UTC) - timedelta(days=30)  # Old
        }

        priority_order = ['error_log']

        # Score with error_analysis template (high recency weight = 0.5)
        recent_score = manager._score_context_item(recent_item, None, priority_order, 'error_analysis')
        old_score = manager._score_context_item(old_item, None, priority_order, 'error_analysis')

        # Recent item should score higher despite lower importance
        assert recent_score > old_score

    def test_fallback_to_default_weights(self, manager):
        """Test fallback to default weights for unknown template."""
        item = {
            'type': 'test',
            'content': 'Test content',
            'priority': 5,
            'timestamp': datetime.now(UTC)
        }

        priority_order = ['test']

        # Score with unknown template
        unknown_score = manager._score_context_item(item, None, priority_order, 'unknown_template')

        # Score without template (should use defaults)
        default_score = manager._score_context_item(item, None, priority_order, None)

        # Should be identical (both use default weights)
        assert unknown_score == default_score

    def test_prioritize_context_accepts_template_name(self, manager):
        """Test that prioritize_context accepts template_name parameter."""
        items = [
            {'type': 'test', 'content': 'Test 1', 'priority': 5},
            {'type': 'test', 'content': 'Test 2', 'priority': 7}
        ]

        # Should not raise error
        prioritized = manager.prioritize_context(items, None, None, 'validation')

        assert len(prioritized) == 2
        assert all(isinstance(score, float) for _, score in prioritized)

    def test_end_to_end_template_weight_differentiation(self, manager, task):
        """Test that different templates produce different prioritization."""
        # Create items with different characteristics
        items = [
            {
                'type': 'recent_error',
                'content': 'error occurred',
                'priority': 3,
                'timestamp': datetime.now(UTC)  # Very recent
            },
            {
                'type': 'test_results',
                'content': 'tests passed',
                'priority': 10,
                'timestamp': datetime.now(UTC) - timedelta(days=20)  # Old but important
            },
            {
                'type': 'code_example',
                'content': 'function to add two numbers',  # High relevance to task
                'priority': 5,
                'timestamp': datetime.now(UTC) - timedelta(days=10)
            }
        ]

        # Prioritize with error_analysis (should favor recent_error)
        error_prioritized = manager.prioritize_context(items, task, None, 'error_analysis')
        error_top_type = error_prioritized[0][0]['type']

        # Prioritize with validation (should favor test_results - high importance)
        validation_prioritized = manager.prioritize_context(items, task, None, 'validation')
        validation_top_type = validation_prioritized[0][0]['type']

        # Prioritize with task_execution (should favor code_example - high relevance)
        task_prioritized = manager.prioritize_context(items, task, None, 'task_execution')
        task_top_type = task_prioritized[0][0]['type']

        # Each template should prioritize differently
        # Error analysis should pick recent error
        assert error_top_type == 'recent_error'

        # Validation should pick test results (high importance)
        assert validation_top_type == 'test_results'

        # Task execution should pick code example (high relevance to task)
        assert task_top_type == 'code_example'
