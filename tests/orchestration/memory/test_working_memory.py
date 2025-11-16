"""Unit tests for WorkingMemory.

Tests cover:
- Initialization and configuration
- Adaptive sizing
- Operation addition and eviction
- Query methods
- Thread safety
- Edge cases

Author: Obra System
Created: 2025-01-15
"""

import pytest
import threading
import time
from datetime import datetime
from src.orchestration.memory.working_memory import (
    WorkingMemory,
    WorkingMemoryException
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def small_context_config():
    """Configuration for small context (4K)."""
    return {'context_window': 4000}


@pytest.fixture
def medium_context_config():
    """Configuration for medium context (16K)."""
    return {'context_window': 16000}


@pytest.fixture
def large_context_config():
    """Configuration for large context (128K)."""
    return {'context_window': 128000}


@pytest.fixture
def huge_context_config():
    """Configuration for huge context (1M)."""
    return {'context_window': 1000000}


@pytest.fixture
def working_memory(medium_context_config):
    """Create a WorkingMemory instance with medium context."""
    return WorkingMemory(medium_context_config)


@pytest.fixture
def sample_operation():
    """Create a sample operation."""
    return {
        'type': 'task',
        'operation': 'create_task',
        'data': {'title': 'Example Task'},
        'tokens': 100
    }


# ============================================================================
# Test: Initialization
# ============================================================================

def test_init_with_valid_config(medium_context_config):
    """Test initialization with valid configuration."""
    memory = WorkingMemory(medium_context_config)

    assert memory.context_window == 16000
    assert memory.max_operations == 30  # From DEFAULT_SIZING
    assert memory.max_tokens == 1120    # 16000 * 0.07
    assert len(memory) == 0


def test_init_with_invalid_config_type():
    """Test initialization with invalid config type."""
    with pytest.raises(WorkingMemoryException) as exc_info:
        WorkingMemory("not a dict")

    assert "must be a dictionary" in str(exc_info.value)


def test_init_with_missing_context_window():
    """Test initialization with missing context_window."""
    with pytest.raises(WorkingMemoryException) as exc_info:
        WorkingMemory({})

    assert "Invalid context_window" in str(exc_info.value)


def test_init_with_invalid_context_window():
    """Test initialization with invalid context_window."""
    with pytest.raises(WorkingMemoryException) as exc_info:
        WorkingMemory({'context_window': -1000})

    assert "Invalid context_window" in str(exc_info.value)


def test_init_with_config_overrides():
    """Test initialization with configuration overrides."""
    config = {
        'context_window': 16000,
        'max_operations': 50,
        'max_tokens': 2000
    }
    memory = WorkingMemory(config)

    assert memory.max_operations == 50
    assert memory.max_tokens == 2000


def test_init_with_max_tokens_pct_override():
    """Test initialization with max_tokens_pct override."""
    config = {
        'context_window': 16000,
        'max_tokens_pct': 0.15  # 15% instead of default 7%
    }
    memory = WorkingMemory(config)

    assert memory.max_tokens == 2400  # 16000 * 0.15


# ============================================================================
# Test: Adaptive Sizing
# ============================================================================

def test_adaptive_sizing_4k_context(small_context_config):
    """Test adaptive sizing for 4K context."""
    memory = WorkingMemory(small_context_config)

    assert memory.max_operations == 10
    assert memory.max_tokens == 200  # 4000 * 0.05


def test_adaptive_sizing_16k_context(medium_context_config):
    """Test adaptive sizing for 16K context."""
    memory = WorkingMemory(medium_context_config)

    assert memory.max_operations == 30
    assert memory.max_tokens == 1120  # 16000 * 0.07


def test_adaptive_sizing_128k_context(large_context_config):
    """Test adaptive sizing for 128K context."""
    memory = WorkingMemory(large_context_config)

    assert memory.max_operations == 50
    assert memory.max_tokens == 12800  # 128000 * 0.10


def test_adaptive_sizing_1m_context(huge_context_config):
    """Test adaptive sizing for 1M context."""
    memory = WorkingMemory(huge_context_config)

    assert memory.max_operations == 100
    assert memory.max_tokens == 100000  # 1000000 * 0.10


def test_adaptive_sizing_very_large_context():
    """Test adaptive sizing for context larger than max default."""
    config = {'context_window': 2000000}  # 2M
    memory = WorkingMemory(config)

    # Should use largest default
    assert memory.max_operations == 100
    assert memory.max_tokens == 200000  # 2000000 * 0.10


# ============================================================================
# Test: Adding Operations
# ============================================================================

def test_add_operation_success(working_memory, sample_operation):
    """Test adding an operation successfully."""
    working_memory.add_operation(sample_operation)

    assert len(working_memory) == 1
    assert working_memory._current_tokens == 100


def test_add_operation_with_timestamp(working_memory):
    """Test that timestamp is added if not present."""
    op = {
        'type': 'task',
        'operation': 'create_task',
        'tokens': 50
    }
    working_memory.add_operation(op)

    operations = working_memory.get_all_operations()
    assert 'timestamp' in operations[0]


def test_add_operation_preserves_timestamp(working_memory):
    """Test that existing timestamp is preserved."""
    timestamp = '2025-01-15T10:00:00'
    op = {
        'type': 'task',
        'operation': 'create_task',
        'tokens': 50,
        'timestamp': timestamp
    }
    working_memory.add_operation(op)

    operations = working_memory.get_all_operations()
    assert operations[0]['timestamp'] == timestamp


def test_add_operation_invalid_type(working_memory):
    """Test adding invalid operation type."""
    with pytest.raises(WorkingMemoryException) as exc_info:
        working_memory.add_operation("not a dict")

    assert "must be a dictionary" in str(exc_info.value)


def test_add_operation_missing_required_fields(working_memory):
    """Test adding operation with missing required fields."""
    op = {'type': 'task'}  # Missing 'operation' and 'tokens'

    with pytest.raises(WorkingMemoryException) as exc_info:
        working_memory.add_operation(op)

    assert "missing required fields" in str(exc_info.value)


def test_add_operation_invalid_tokens(working_memory):
    """Test adding operation with invalid token count."""
    op = {
        'type': 'task',
        'operation': 'create_task',
        'tokens': -50  # Negative tokens
    }

    with pytest.raises(WorkingMemoryException) as exc_info:
        working_memory.add_operation(op)

    assert "Invalid token count" in str(exc_info.value)


def test_add_multiple_operations(working_memory):
    """Test adding multiple operations."""
    for i in range(5):
        op = {
            'type': 'task',
            'operation': f'task_{i}',
            'tokens': 100
        }
        working_memory.add_operation(op)

    assert len(working_memory) == 5
    assert working_memory._current_tokens == 500


# ============================================================================
# Test: FIFO Eviction
# ============================================================================

def test_eviction_when_max_operations_exceeded(small_context_config):
    """Test FIFO eviction when max operations exceeded."""
    memory = WorkingMemory(small_context_config)
    # max_operations = 10 for 4K context

    # Add 12 operations
    for i in range(12):
        op = {
            'type': 'task',
            'operation': f'task_{i}',
            'tokens': 10
        }
        memory.add_operation(op)

    # Should only keep last 10
    assert len(memory) == 10
    assert memory._eviction_count == 2

    # Verify oldest were evicted (tasks 0 and 1)
    operations = memory.get_all_operations()
    assert operations[0]['operation'] == 'task_2'
    assert operations[-1]['operation'] == 'task_11'


def test_eviction_when_max_tokens_exceeded(small_context_config):
    """Test FIFO eviction when max tokens exceeded."""
    memory = WorkingMemory(small_context_config)
    # max_tokens = 200 for 4K context

    # Add operations totaling more than 200 tokens
    for i in range(5):
        op = {
            'type': 'task',
            'operation': f'task_{i}',
            'tokens': 60  # 5 * 60 = 300 tokens total
        }
        memory.add_operation(op)

    # Should evict to stay under max_tokens
    assert memory._current_tokens <= 200
    assert memory._eviction_count > 0


def test_eviction_updates_token_count(small_context_config):
    """Test that eviction properly updates token count."""
    memory = WorkingMemory(small_context_config)

    # Add operation
    op1 = {'type': 'task', 'operation': 'task_1', 'tokens': 50}
    memory.add_operation(op1)
    assert memory._current_tokens == 50

    # Fill up and trigger eviction
    for i in range(2, 15):
        op = {'type': 'task', 'operation': f'task_{i}', 'tokens': 20}
        memory.add_operation(op)

    # Token count should be accurate after evictions
    operations = memory.get_all_operations()
    expected_tokens = sum(op['tokens'] for op in operations)
    assert memory._current_tokens == expected_tokens


def test_eviction_order_fifo(working_memory):
    """Test that eviction follows FIFO order."""
    # Add operations with unique data
    for i in range(50):  # More than max_operations
        op = {
            'type': 'task',
            'operation': f'task_{i}',
            'data': {'id': i},
            'tokens': 10
        }
        working_memory.add_operation(op)

    # Check that oldest operations were evicted
    operations = working_memory.get_all_operations()
    first_remaining = operations[0]['data']['id']
    last_remaining = operations[-1]['data']['id']

    assert last_remaining == 49  # Last added
    assert first_remaining > 0   # First ones evicted


# ============================================================================
# Test: Query Methods
# ============================================================================

def test_get_all_operations(working_memory):
    """Test getting all operations in chronological order."""
    for i in range(3):
        op = {'type': 'task', 'operation': f'task_{i}', 'tokens': 10}
        working_memory.add_operation(op)

    operations = working_memory.get_all_operations()

    assert len(operations) == 3
    assert operations[0]['operation'] == 'task_0'  # Oldest first
    assert operations[2]['operation'] == 'task_2'  # Newest last


def test_get_recent_operations_no_limit(working_memory):
    """Test getting recent operations without limit."""
    for i in range(3):
        op = {'type': 'task', 'operation': f'task_{i}', 'tokens': 10}
        working_memory.add_operation(op)

    recent = working_memory.get_recent_operations()

    assert len(recent) == 3
    assert recent[0]['operation'] == 'task_2'  # Newest first
    assert recent[2]['operation'] == 'task_0'  # Oldest last


def test_get_recent_operations_with_limit(working_memory):
    """Test getting recent operations with limit."""
    for i in range(5):
        op = {'type': 'task', 'operation': f'task_{i}', 'tokens': 10}
        working_memory.add_operation(op)

    recent = working_memory.get_recent_operations(limit=2)

    assert len(recent) == 2
    assert recent[0]['operation'] == 'task_4'
    assert recent[1]['operation'] == 'task_3'


def test_get_operations_by_type(working_memory):
    """Test filtering operations by type."""
    # Add mix of operation types
    working_memory.add_operation({'type': 'task', 'operation': 'task_1', 'tokens': 10})
    working_memory.add_operation({'type': 'nl_command', 'operation': 'cmd_1', 'tokens': 10})
    working_memory.add_operation({'type': 'task', 'operation': 'task_2', 'tokens': 10})
    working_memory.add_operation({'type': 'nl_command', 'operation': 'cmd_2', 'tokens': 10})

    task_ops = working_memory.get_operations(operation_type='task')
    cmd_ops = working_memory.get_operations(operation_type='nl_command')

    assert len(task_ops) == 2
    assert len(cmd_ops) == 2
    assert all(op['type'] == 'task' for op in task_ops)
    assert all(op['type'] == 'nl_command' for op in cmd_ops)


def test_get_operations_with_limit(working_memory):
    """Test filtering operations with limit."""
    for i in range(5):
        working_memory.add_operation({'type': 'task', 'operation': f'task_{i}', 'tokens': 10})

    operations = working_memory.get_operations(operation_type='task', limit=2)

    assert len(operations) == 2
    assert operations[0]['operation'] == 'task_4'  # Most recent first


def test_get_operations_no_type_filter(working_memory):
    """Test get_operations without type filter returns recent."""
    for i in range(3):
        working_memory.add_operation({'type': 'task', 'operation': f'task_{i}', 'tokens': 10})

    operations = working_memory.get_operations(operation_type=None, limit=10)

    assert len(operations) == 3


def test_search_by_keyword(working_memory):
    """Test searching operations by keyword."""
    working_memory.add_operation({
        'type': 'task',
        'operation': 'create_task',
        'data': {'title': 'Implement login feature'},
        'tokens': 10
    })
    working_memory.add_operation({
        'type': 'task',
        'operation': 'create_task',
        'data': {'title': 'Add user dashboard'},
        'tokens': 10
    })
    working_memory.add_operation({
        'type': 'task',
        'operation': 'create_task',
        'data': {'title': 'Update login page'},
        'tokens': 10
    })

    results = working_memory.search('login')

    assert len(results) == 2
    assert 'login' in results[0].lower() or 'login' in results[1].lower()


def test_search_case_insensitive(working_memory):
    """Test that search is case-insensitive."""
    working_memory.add_operation({
        'type': 'task',
        'operation': 'create_task',
        'data': {'title': 'LOGIN Feature'},
        'tokens': 10
    })

    results_lower = working_memory.search('login')
    results_upper = working_memory.search('LOGIN')
    results_mixed = working_memory.search('LoGiN')

    assert len(results_lower) == len(results_upper) == len(results_mixed) == 1


def test_search_with_max_results(working_memory):
    """Test search respects max_results limit."""
    for i in range(10):
        working_memory.add_operation({
            'type': 'task',
            'operation': 'create_task',
            'data': {'title': f'Task {i}'},
            'tokens': 10
        })

    results = working_memory.search('task', max_results=3)

    assert len(results) == 3


def test_search_no_matches(working_memory):
    """Test search with no matches."""
    working_memory.add_operation({
        'type': 'task',
        'operation': 'create_task',
        'data': {'title': 'Example'},
        'tokens': 10
    })

    results = working_memory.search('nonexistent')

    assert len(results) == 0


# ============================================================================
# Test: Clear and Status
# ============================================================================

def test_clear(working_memory):
    """Test clearing all operations."""
    for i in range(3):
        working_memory.add_operation({'type': 'task', 'operation': f'task_{i}', 'tokens': 10})

    working_memory.clear()

    assert len(working_memory) == 0
    assert working_memory._current_tokens == 0


def test_get_status(working_memory):
    """Test getting status information."""
    working_memory.add_operation({'type': 'task', 'operation': 'task_1', 'tokens': 100})
    working_memory.add_operation({'type': 'task', 'operation': 'task_2', 'tokens': 200})

    status = working_memory.get_status()

    assert status['operation_count'] == 2
    assert status['max_operations'] == 30
    assert status['current_tokens'] == 300
    assert status['max_tokens'] == 1120
    assert 0 < status['token_utilization'] < 1
    assert status['context_window'] == 16000


def test_len(working_memory):
    """Test __len__ method."""
    assert len(working_memory) == 0

    working_memory.add_operation({'type': 'task', 'operation': 'task_1', 'tokens': 10})
    assert len(working_memory) == 1

    working_memory.add_operation({'type': 'task', 'operation': 'task_2', 'tokens': 10})
    assert len(working_memory) == 2


def test_repr(working_memory):
    """Test __repr__ method."""
    working_memory.add_operation({'type': 'task', 'operation': 'task_1', 'tokens': 100})

    repr_str = repr(working_memory)

    assert 'WorkingMemory' in repr_str
    assert 'ops=1/30' in repr_str
    assert 'tokens=100/1120' in repr_str


# ============================================================================
# Test: Thread Safety
# ============================================================================

def test_concurrent_adds(medium_context_config, fast_time):
    """Test concurrent operation additions."""
    memory = WorkingMemory(medium_context_config)
    num_threads = 5
    ops_per_thread = 10

    def add_operations(thread_id):
        for i in range(ops_per_thread):
            op = {
                'type': 'task',
                'operation': f'thread_{thread_id}_op_{i}',
                'tokens': 10
            }
            memory.add_operation(op)

    threads = [threading.Thread(target=add_operations, args=(i,)) for i in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    # All operations should be added (or evicted if over limit)
    assert len(memory) <= memory.max_operations
    assert memory._current_tokens <= memory.max_tokens


def test_concurrent_reads_and_writes(medium_context_config, fast_time):
    """Test concurrent reads and writes."""
    memory = WorkingMemory(medium_context_config)
    errors = []

    def writer():
        try:
            for i in range(20):
                op = {'type': 'task', 'operation': f'task_{i}', 'tokens': 10}
                memory.add_operation(op)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for _ in range(20):
                _ = memory.get_recent_operations(limit=5)
                _ = memory.get_status()
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=writer),
        threading.Thread(target=reader),
        threading.Thread(target=reader)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(errors) == 0


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_add_operation_with_zero_tokens(working_memory):
    """Test adding operation with zero tokens."""
    op = {'type': 'task', 'operation': 'task_1', 'tokens': 0}
    working_memory.add_operation(op)

    assert len(working_memory) == 1
    assert working_memory._current_tokens == 0


def test_add_very_large_operation(small_context_config):
    """Test adding operation that exceeds max_tokens."""
    memory = WorkingMemory(small_context_config)
    # max_tokens = 200

    op = {'type': 'task', 'operation': 'huge_task', 'tokens': 300}
    memory.add_operation(op)

    # Should evict all previous operations and still add it
    assert len(memory) == 1
    assert memory._current_tokens == 300  # Exceeds max, but operation added


def test_empty_operations_query(working_memory):
    """Test querying when no operations exist."""
    assert working_memory.get_all_operations() == []
    assert working_memory.get_recent_operations() == []
    assert working_memory.get_operations(operation_type='task') == []
    assert working_memory.search('test') == []


def test_eviction_count_tracking(small_context_config):
    """Test that eviction count is tracked correctly."""
    memory = WorkingMemory(small_context_config)

    # Add enough operations to trigger evictions
    for i in range(20):  # max_operations = 10
        op = {'type': 'task', 'operation': f'task_{i}', 'tokens': 10}
        memory.add_operation(op)

    status = memory.get_status()
    assert status['eviction_count'] == 10  # 20 - 10 = 10 evictions
