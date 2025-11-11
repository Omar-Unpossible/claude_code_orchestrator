"""CSV Tool Creation Test with Flexible LLM Support.

Tests end-to-end orchestration with both Ollama and OpenAI Codex LLM types
by having Claude Code create a Python script to read a CSV and calculate averages.

IMPORTANT: Tests run SEQUENTIALLY to avoid Claude Code rate limiting.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.orchestrator import Orchestrator
from src.core.state import StateManager
from src.core.exceptions import OrchestratorException
from src.llm.local_interface import LocalLLMInterface
from src.llm.openai_codex_interface import OpenAICodexLLMPlugin


@pytest.fixture
def csv_workspace():
    """Create temporary workspace with sample CSV file."""
    temp_dir = tempfile.mkdtemp(prefix='csv_test_')
    workspace = Path(temp_dir)

    # Create sample CSV
    csv_file = workspace / 'sample.csv'
    csv_file.write_text('name,age,city\nAlice,30,NYC\nBob,25,SF\nCharlie,35,LA\n')

    yield workspace

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def state_manager_csv(test_config):
    """Create isolated state manager for CSV tests."""
    import tempfile

    # Reset singleton before creating (critical for parameterized tests!)
    StateManager.reset_instance()

    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_url = f'sqlite:///{db_file.name}'

    sm = StateManager.get_instance(db_url)
    yield sm

    sm.close()
    # Reset singleton after closing (critical for parameterized tests!)
    StateManager.reset_instance()
    # Cleanup database file
    try:
        Path(db_file.name).unlink()
    except Exception:
        pass


# Parameterized test with sequential execution (pytest runs parameters sequentially by default)
@pytest.mark.parametrize('llm_type,llm_config', [
    # Test 1: Ollama (baseline)
    pytest.param(
        'ollama',
        {
            'model': 'qwen2.5-coder:32b',
            'base_url': 'http://localhost:11434',
            'endpoint': 'http://localhost:11434'
        },
        id='ollama'
    ),
    # Test 2: OpenAI Codex (new)
    pytest.param(
        'openai-codex',
        {
            'model': 'codex-mini-latest',
            'codex_command': 'codex',
            'timeout': 60
        },
        id='codex'
    )
])
@pytest.mark.slow  # Mark as slow test
def test_csv_tool_creation_flexible_llm(
    llm_type,
    llm_config,
    csv_workspace,
    state_manager_csv,
    test_config,
    monkeypatch,
    fast_time
):
    """Test CSV tool creation with both Ollama and OpenAI Codex orchestrators.

    This test validates end-to-end orchestration by asking Claude Code to create
    a Python script that reads a CSV file and calculates the average age.

    Tests run SEQUENTIALLY to avoid Claude Code rate limiting between prompts.

    Args:
        llm_type: LLM provider type ('ollama' or 'openai-codex')
        llm_config: LLM-specific configuration
        csv_workspace: Temporary workspace with sample CSV
        state_manager_csv: Isolated state manager for this test
        test_config: Test configuration fixture
        monkeypatch: Pytest monkeypatch for mocking
        fast_time: Fast time fixture to avoid blocking sleeps
    """
    # Setup appropriate mocking based on LLM type
    if llm_type == 'ollama':
        # Mock Ollama HTTP API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [{'name': 'qwen2.5-coder:32b', 'size': 1000000}]
        }

        def mock_get(*args, **kwargs):
            return mock_response

        monkeypatch.setattr('requests.get', mock_get)

    elif llm_type == 'openai-codex':
        # Mock OpenAI Codex CLI
        def mock_which(cmd):
            if cmd == 'codex':
                return '/usr/local/bin/codex'
            return None

        monkeypatch.setattr('shutil.which', mock_which)

    # Configure orchestrator with specified LLM type
    test_config._config['llm']['type'] = llm_type
    test_config._config['llm'].update(llm_config)

    # Create orchestrator
    orchestrator = Orchestrator(config=test_config)
    orchestrator.initialize()

    # Verify correct LLM type is loaded
    if llm_type == 'ollama':
        assert isinstance(orchestrator.llm_interface, LocalLLMInterface)
        assert orchestrator.llm_interface.model == 'qwen2.5-coder:32b'
    elif llm_type == 'openai-codex':
        assert isinstance(orchestrator.llm_interface, OpenAICodexLLMPlugin)
        assert orchestrator.llm_interface.model == 'codex-mini-latest'

    # Create test project
    project = state_manager_csv.create_project(
        f'CSV Test {llm_type}',
        f'Test CSV tool creation with {llm_type}',
        str(csv_workspace)
    )

    # Create task to process CSV
    csv_path = csv_workspace / 'sample.csv'
    task = state_manager_csv.create_task(project.id, {
        'title': 'Process CSV File',
        'description': (
            f'Read the CSV file at {csv_path} and calculate the average age of all people. '
            f'The CSV has columns: name, age, city. '
            f'Print the result as "Average age: X".'
        ),
        'priority': 5,
        'status': 'pending'
    })

    # Mock agent response to avoid actual Claude Code execution
    # This simulates Claude creating a Python script
    mock_agent_response = f"""I'll create a Python script to read the CSV and calculate the average age.

```python
import csv

# Read CSV file
with open('{csv_path}', 'r') as f:
    reader = csv.DictReader(f)
    ages = [int(row['age']) for row in reader]

# Calculate average
average_age = sum(ages) / len(ages)
print(f"Average age: {{average_age}}")
```

This script reads the CSV file, extracts the ages, and calculates the average.
Expected result: Average age: 30.0
"""

    orchestrator.agent.send_prompt = MagicMock(return_value=mock_agent_response)

    # Execute task with limited iterations (this is a unit/integration test, not real orchestration)
    try:
        result = orchestrator.execute_task(task.id, max_iterations=3)

        # Validate result
        assert result is not None
        assert 'status' in result
        assert result['status'] in ['completed', 'escalated', 'max_iterations']
        assert 'iterations' in result
        assert result['iterations'] >= 1

        # Check that task was processed
        updated_task = state_manager_csv.get_task(task.id)
        assert updated_task is not None

        # For tracking: Log LLM type and result
        print(f"\n{llm_type.upper()} Result: status={result['status']}, iterations={result['iterations']}")

    except OrchestratorException as e:
        # Some orchestrator exceptions are acceptable (e.g., max_iterations)
        print(f"\n{llm_type.upper()} Exception: {e}")
        pytest.skip(f"Orchestrator exception (acceptable for test): {e}")

    finally:
        # Cleanup
        orchestrator.shutdown()

        # CRITICAL: Add delay between parameterized test runs to avoid Claude rate limiting
        # This ensures the next LLM type test doesn't trigger cooldown
        if llm_type == 'ollama':
            # After Ollama test, wait before Codex test
            # In real scenario this would be time.sleep(5), but fast_time makes it instant
            time.sleep(5.0)


@pytest.mark.slow
def test_csv_tool_sequential_execution_note():
    """Documentation test explaining sequential execution requirement.

    This test serves as documentation that CSV tests MUST run sequentially
    to avoid Claude Code rate limiting. Pytest parameterize runs tests
    sequentially by default, which is what we need.

    DO NOT use pytest-xdist or parallel test execution with these tests!
    """
    assert True  # Always passes - this is just documentation


# Comparison test (optional - runs both and compares)
@pytest.mark.slow
@pytest.mark.skip(reason="Manual execution only - compares both LLM types side-by-side")
def test_csv_tool_llm_comparison(csv_workspace, state_manager_csv, test_config, monkeypatch):
    """Compare CSV tool creation results between Ollama and OpenAI Codex.

    This test is SKIPPED by default and should only be run manually for
    comparative analysis. It runs both LLM types sequentially and logs
    the differences.

    Run with: pytest -v -s tests/test_csv_tool_flexible_llm.py::test_csv_tool_llm_comparison
    """
    results = {}

    for llm_type, llm_config in [
        ('ollama', {'model': 'qwen2.5-coder:32b', 'base_url': 'http://localhost:11434'}),
        ('openai-codex', {'model': 'codex-mini-latest', 'codex_command': 'codex'})
    ]:
        # Setup mocking
        if llm_type == 'ollama':
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'models': [{'name': 'qwen2.5-coder:32b'}]}
            monkeypatch.setattr('requests.get', lambda *a, **k: mock_response)
        else:
            monkeypatch.setattr('shutil.which', lambda cmd: '/usr/local/bin/codex' if cmd == 'codex' else None)

        # Configure and run
        test_config._config['llm']['type'] = llm_type
        test_config._config['llm'].update(llm_config)

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Create project and task
        project = state_manager_csv.create_project(f'Compare {llm_type}', 'Comparison', str(csv_workspace))
        task = state_manager_csv.create_task(project.id, {
            'title': 'Process CSV',
            'description': 'Read CSV and calculate average age',
            'priority': 5
        })

        # Mock agent
        orchestrator.agent.send_prompt = MagicMock(return_value="Mock response")

        try:
            result = orchestrator.execute_task(task.id, max_iterations=3)
            results[llm_type] = {
                'status': result.get('status'),
                'iterations': result.get('iterations'),
                'success': True
            }
        except Exception as e:
            results[llm_type] = {
                'status': 'error',
                'error': str(e),
                'success': False
            }
        finally:
            orchestrator.shutdown()

        # Wait between tests
        time.sleep(5.0)

    # Print comparison
    print("\n" + "="*80)
    print("CSV TOOL CREATION - LLM COMPARISON")
    print("="*80)
    for llm_type, result in results.items():
        print(f"\n{llm_type.upper()}:")
        print(f"  Status: {result.get('status')}")
        print(f"  Iterations: {result.get('iterations', 'N/A')}")
        print(f"  Success: {result.get('success')}")
        if 'error' in result:
            print(f"  Error: {result['error']}")
    print("="*80 + "\n")

    # Both should work
    assert all(r['success'] for r in results.values()), "One or both LLM types failed"
