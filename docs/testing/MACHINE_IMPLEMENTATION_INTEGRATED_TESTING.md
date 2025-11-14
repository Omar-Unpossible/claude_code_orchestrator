# Machine-Optimized: Integrated NL Testing Implementation

**Target**: Claude Code Agent (Autonomous Execution)
**Philosophy**: REAL Testing First - Mocks for Initial Validation Only
**Estimated Time**: 80 hours across 10 days (phased execution)
**Prerequisites**: Python 3.9+, pytest, Ollama with Qwen 2.5 Coder, Claude Code CLI

---

## Quick Start

```bash
# Verify prerequisites
pytest --version  # Should be 7.0+
python --version  # Should be 3.9+
curl http://10.0.75.1:11434/api/tags  # Should return Ollama models

# Set environment
export OLLAMA_ENDPOINT=http://10.0.75.1:11434
export OLLAMA_MODEL=qwen2.5-coder:32b
export TEST_DATABASE_URL=sqlite:///:memory:

# Begin Phase 0
pytest tests/integration/test_orchestrator_nl_integration.py -v  # Expect 10/12 failures
```

---

## PHASE 0: Fix Broken Tests (4 hours) 🔥 IMMEDIATE

### Task 0.1: Fix Integration Tests (2 hours)

**File**: `tests/integration/test_orchestrator_nl_integration.py`

**Find and Replace** (10 occurrences):

```python
# FIND (line ~113, 134, 159, 183, 240, 265, 294, 314, 363, 390):
operation_context = OperationContext(
    operation=OperationType.CREATE,
    entity_type=EntityType.EPIC,  # OLD API ❌
    ...
)

# REPLACE WITH:
operation_context = OperationContext(
    operation=OperationType.CREATE,
    entity_types=[EntityType.EPIC],  # NEW API ✅
    ...
)
```

**Verification**:
```bash
pytest tests/integration/test_orchestrator_nl_integration.py -v
# Expected: 12/12 passing (was 2/12)
```

### Task 0.2: Fix Smoke Tests (2 hours)

**File**: `tests/smoke/test_smoke_workflows.py`

**Issue**: `test_create_epic_smoke` returns `intent='QUESTION'` instead of `'COMMAND'`

**Debug**:
```python
# Add logging to test to see where pipeline fails
def test_create_epic_smoke(self, nl_processor, mock_llm_smart):
    import logging
    logging.basicConfig(level=logging.DEBUG)

    response = nl_processor.process("create epic for user auth")

    # Debug output
    print(f"Intent: {response.intent_type}")
    print(f"Error: {response.metadata.get('processing_error')}")

    # Run with: pytest tests/smoke/test_smoke_workflows.py::TestSmokeWorkflows::test_create_epic_smoke -vvs
```

**Likely Fix Location**: `src/nl/nl_command_processor.py` around line 200-250

**Fix Pattern**: Ensure `OperationContext` is properly constructed from classifier results

**Verification**:
```bash
pytest tests/smoke/test_smoke_workflows.py -v
# Expected: 10/10 passing (was 7/10)
```

**Commit**:
```bash
git add tests/integration/test_orchestrator_nl_integration.py tests/smoke/test_smoke_workflows.py
git commit -m "fix: Update tests for v1.7.5 API (entity_types list)

- Fixed 10 integration tests: entity_type → entity_types
- Fixed 3 smoke tests: pipeline OperationContext construction
- All existing tests now pass (baseline established)

PHASE 0 COMPLETE: Ready for real component testing"
```

---

## PHASE 1: Real Component Integration (8 hours) ⚙️

### Task 1.1: Create Real Component Fixtures (1 hour)

**File**: `tests/conftest.py` (APPEND to end)

```python
# ==================== REAL COMPONENT FIXTURES (Phase 1) ====================

@pytest.fixture
def real_state_manager():
    """REAL StateManager with in-memory SQLite.

    Use this instead of mocks for integration tests.
    Provides actual database operations with zero persistence.
    """
    state = StateManager(database_url='sqlite:///:memory:')
    yield state
    state.close()

@pytest.fixture
def real_nl_processor(real_state_manager, mock_llm_realistic):
    """REAL NLCommandProcessor with realistic mock LLM.

    Uses REAL StateManager and REAL processing logic.
    Only LLM responses are mocked (but realistic).
    """
    return NLCommandProcessor(
        llm_plugin=mock_llm_realistic,
        state_manager=real_state_manager,
        config={'nl_commands': {'enabled': True}}
    )

@pytest.fixture
def mock_llm_realistic():
    """Mock LLM with REALISTIC responses matching Qwen 2.5 Coder output.

    Responses match actual LLM output format for controlled testing.
    """
    from unittest.mock import MagicMock

    llm = MagicMock()

    # Response templates matching Qwen 2.5 Coder output format
    def generate_realistic(prompt, **kwargs):
        # Intent classification
        if "intent" in prompt.lower():
            if any(word in prompt.lower() for word in ["create", "add", "make"]):
                return '{"intent": "COMMAND", "confidence": 0.95}'
            else:
                return '{"intent": "QUESTION", "confidence": 0.93}'

        # Operation classification
        if "operation" in prompt.lower():
            if "create" in prompt.lower() or "add" in prompt.lower():
                return '{"operation_type": "CREATE", "confidence": 0.94}'
            elif "list" in prompt.lower() or "show" in prompt.lower():
                return '{"operation_type": "QUERY", "confidence": 0.96}'
            elif "update" in prompt.lower() or "change" in prompt.lower():
                return '{"operation_type": "UPDATE", "confidence": 0.93}'
            elif "delete" in prompt.lower() or "remove" in prompt.lower():
                return '{"operation_type": "DELETE", "confidence": 0.94}'

        # Entity type classification
        if "entity_type" in prompt.lower():
            if "epic" in prompt.lower():
                return '{"entity_types": ["EPIC"], "confidence": 0.96}'
            elif "story" in prompt.lower() or "stories" in prompt.lower():
                return '{"entity_types": ["STORY"], "confidence": 0.94}'
            elif "task" in prompt.lower():
                return '{"entity_types": ["TASK"], "confidence": 0.95}'
            elif "project" in prompt.lower():
                return '{"entity_types": ["PROJECT"], "confidence": 0.97}'
            elif "milestone" in prompt.lower():
                return '{"entity_types": ["MILESTONE"], "confidence": 0.93}'

        # Entity identifier extraction
        if "identifier" in prompt.lower():
            import re
            match = re.search(r'\b(\d+)\b', prompt)
            if match:
                return f'{{"identifier": {match.group(1)}, "confidence": 0.98}}'
            return '{"identifier": null, "confidence": 0.92}'

        # Parameter extraction
        if "parameters" in prompt.lower():
            params = {}
            if "title" in prompt.lower():
                # Extract quoted title or capitalize words
                params["title"] = "Generated Title"
            return f'{{"parameters": {params}, "confidence": 0.90}}'

        return '{"result": "unknown", "confidence": 0.5}'

    llm.generate.side_effect = generate_realistic
    return llm
```

**Verification**:
```bash
pytest tests/conftest.py --collect-only
# Should show new fixtures available
```

### Task 1.2: Create Real Component Workflow Tests (7 hours)

**File**: `tests/integration/test_nl_workflows_real_components.py` (CREATE NEW)

```python
"""Real component workflow tests (mock LLM only).

These tests use REAL StateManager, REAL NLCommandProcessor, REAL NLQueryHelper.
Only the LLM is mocked (with realistic responses).

Purpose: Validate component integration before expensive real LLM tests.
NOT "done" criteria: Need real LLM tests to pass.
"""

import pytest
from src.core.models import TaskType, TaskStatus
from src.nl.types import EntityType, OperationType


class TestProjectWorkflowsRealComponents:
    """Project-level workflows with real components."""

    def test_list_projects_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'list all projects' → actual project list"""
        # Create 3 test projects
        for i in range(3):
            real_state_manager.create_project(
                project_name=f"Project {i}",
                description=f"Description {i}"
            )

        # Execute NL command through REAL processor
        response = real_nl_processor.process("list all projects")

        # Validate complete response structure
        assert response.success, f"Failed: {response.error_message}"
        assert response.intent_type == 'COMMAND'
        assert len(response.results.entities) == 3

    def test_query_project_statistics_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'show project stats' → counts and percentages"""
        project_id = real_state_manager.create_project("Test", "Test")

        # Create various entities
        real_state_manager.create_epic(project_id, "Epic 1", "Desc")
        real_state_manager.create_task(project_id, {'title': 'Task 1'})
        real_state_manager.create_task(project_id, {'title': 'Task 2'})

        response = real_nl_processor.process(
            "show me project statistics",
            context={'project_id': project_id}
        )

        assert response.success
        stats = response.results
        assert stats['total_tasks'] >= 3  # epic + 2 tasks


class TestEpicStoryTaskCreationRealComponents:
    """Work item creation workflows with real components."""

    def test_create_epic_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'create epic for auth' → epic in DB"""
        project_id = real_state_manager.create_project("Test Project", "desc")

        response = real_nl_processor.process(
            "create epic for user authentication",
            context={'project_id': project_id}
        )

        # Validate response
        assert response.success
        assert len(response.execution_result.created_ids) == 1

        # Validate in actual database
        epic_id = response.execution_result.created_ids[0]
        epic = real_state_manager.get_task(epic_id)
        assert epic is not None
        assert epic.task_type == TaskType.EPIC
        assert "auth" in epic.title.lower()

    def test_create_story_in_epic_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'add story to epic 5' → story linked to epic"""
        project_id = real_state_manager.create_project("Test", "Test")
        epic_id = real_state_manager.create_epic(project_id, "Epic", "Desc")

        response = real_nl_processor.process(
            f"add story for password reset to epic {epic_id}",
            context={'project_id': project_id}
        )

        assert response.success
        story_id = response.execution_result.created_ids[0]
        story = real_state_manager.get_task(story_id)
        assert story.task_type == TaskType.STORY
        assert story.epic_id == epic_id

    def test_create_task_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'create task for login' → task created"""
        project_id = real_state_manager.create_project("Test", "Test")

        response = real_nl_processor.process(
            "create task for implementing login form",
            context={'project_id': project_id}
        )

        assert response.success
        task_id = response.execution_result.created_ids[0]
        task = real_state_manager.get_task(task_id)
        assert task.task_type == TaskType.TASK
        assert "login" in task.title.lower()


class TestModificationWorkflowsRealComponents:
    """Update/delete workflows with real components."""

    def test_update_task_status_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'mark task 42 as complete' → status updated"""
        project_id = real_state_manager.create_project("Test", "Test")
        task_id = real_state_manager.create_task(
            project_id,
            {'title': 'Test Task', 'status': TaskStatus.PENDING}
        )

        response = real_nl_processor.process(
            f"mark task {task_id} as complete",
            context={'project_id': project_id}
        )

        assert response.success
        task = real_state_manager.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_delete_single_task_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'delete task 42' → confirmation → deleted"""
        project_id = real_state_manager.create_project("Test", "Test")
        task_id = real_state_manager.create_task(project_id, {'title': 'To Delete'})

        response = real_nl_processor.process(
            f"delete task {task_id}",
            context={'project_id': project_id, 'skip_confirmation': True}
        )

        assert response.success
        task = real_state_manager.get_task(task_id)
        assert task is None or task.status == TaskStatus.DELETED


class TestBulkOperationsRealComponents:
    """Bulk operations with real components."""

    def test_bulk_delete_with_confirmation_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'delete all tasks in project' → confirms → deletes"""
        project_id = real_state_manager.create_project("Test", "Test")

        # Create 5 tasks
        for i in range(5):
            real_state_manager.create_task(project_id, {'title': f'Task {i}'})

        response = real_nl_processor.process(
            "delete all tasks",
            context={'project_id': project_id, 'skip_confirmation': True}
        )

        assert response.success
        remaining_tasks = real_state_manager.list_tasks(project_id)
        assert len([t for t in remaining_tasks if t.status != TaskStatus.DELETED]) == 0


# ... Add 10 more workflow tests to reach 15 total

```

**Run Tests**:
```bash
pytest tests/integration/test_nl_workflows_real_components.py -v
# Expected: 15/15 passing
```

**Commit**:
```bash
git add tests/conftest.py tests/integration/test_nl_workflows_real_components.py
git commit -m "feat: Add real component integration tests (Phase 1)

- Added 15 workflow tests with REAL StateManager and NLCommandProcessor
- Uses realistic mock LLM (matches Qwen output format)
- Validates component integration before expensive real LLM tests

PHASE 1 COMPLETE: Component integration validated"
```

---

## PHASE 2: Real LLM Infrastructure (12 hours) ⭐ CRITICAL

### Task 2.1: Real LLM Fixtures (2 hours)

**File**: `tests/conftest.py` (APPEND)

```python
# ==================== REAL LLM FIXTURES (Phase 2) ====================

@pytest.fixture
def real_ollama_llm():
    """REAL Qwen 2.5 Coder LLM on Ollama.

    This is the TRUE test - uses actual LLM, not mocks.
    Skips test gracefully if Ollama unavailable (for CI).

    Environment:
        OLLAMA_ENDPOINT: http://10.0.75.1:11434 (default)
        OLLAMA_MODEL: qwen2.5-coder:32b (default)
    """
    import os
    from src.llm.local_interface import LocalLLMInterface

    endpoint = os.getenv('OLLAMA_ENDPOINT', 'http://10.0.75.1:11434')
    model = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:32b')

    try:
        llm = LocalLLMInterface(
            endpoint=endpoint,
            model=model,
            temperature=0.1  # Deterministic for testing
        )

        # Health check
        llm.generate("test", max_tokens=5)
        return llm

    except Exception as e:
        pytest.skip(f"Ollama unavailable at {endpoint}: {e}")

@pytest.fixture
def real_orchestrator(real_ollama_llm, test_config):
    """REAL Orchestrator with REAL LLM.

    This is the complete production stack for acceptance testing.
    """
    orchestrator = Orchestrator(config=test_config)
    orchestrator.llm_provider = real_ollama_llm
    return orchestrator

@pytest.fixture
def real_nl_processor_with_llm(real_state_manager, real_ollama_llm):
    """REAL NLCommandProcessor with REAL LLM."""
    return NLCommandProcessor(
        llm_plugin=real_ollama_llm,
        state_manager=real_state_manager,
        config={'nl_commands': {'enabled': True}}
    )
```

**Verification**:
```bash
pytest tests/conftest.py::test_real_ollama_llm --co
# Should show fixture available (or skip if Ollama down)
```

### Task 2.2: Real LLM Acceptance Tests (10 hours)

**File**: `tests/integration/test_nl_workflows_real_llm.py` (CREATE NEW)

```python
"""Complete workflows with REAL Qwen 2.5 Coder LLM.

⭐ THESE ARE THE TRUE ACCEPTANCE TESTS ⭐

Work is NOT "done" until these pass. These tests use:
- REAL Qwen 2.5 Coder LLM (via Ollama)
- REAL StateManager (SQLite)
- REAL Orchestrator (full pipeline)
- REAL user commands (natural language)

If Ollama is unavailable, tests are skipped (not failed).
"""

import pytest
from src.core.models import TaskType, TaskStatus


@pytest.mark.requires_ollama
@pytest.mark.real_llm
@pytest.mark.acceptance
class TestRealLLMProjectWorkflows:
    """Project workflows - ACCEPTANCE TESTS"""

    def test_list_projects_real_llm(self, real_orchestrator):
        """ACCEPTANCE: User can list projects with natural language"""
        # Create test data
        for i in range(3):
            real_orchestrator.state_manager.create_project(
                project_name=f"Project {i}",
                description=f"Description {i}"
            )

        # Execute with REAL LLM - various phrasings
        test_inputs = [
            "show me all projects",
            "list all projects",
            "what projects do I have"
        ]

        for user_input in test_inputs:
            result = real_orchestrator.execute_nl_command(user_input, project_id=1)

            assert result['success'], f"Failed for '{user_input}': {result.get('error')}"
            assert 'Project 0' in result['message']
            assert 'Project 1' in result['message']
            assert 'Project 2' in result['message']

    def test_query_project_statistics_real_llm(self, real_orchestrator):
        """ACCEPTANCE: User can query project statistics"""
        project_id = real_orchestrator.state_manager.create_project("Test", "Test")

        # Create various entities
        real_orchestrator.state_manager.create_epic(project_id, "Epic", "Desc")
        real_orchestrator.state_manager.create_task(project_id, {'title': 'Task 1'})
        real_orchestrator.state_manager.create_task(project_id, {'title': 'Task 2'})

        result = real_orchestrator.execute_nl_command(
            "show me the stats for this project",
            project_id=project_id
        )

        assert result['success']
        assert 'stats' in result['message'].lower() or 'statistics' in result['message'].lower()


@pytest.mark.requires_ollama
@pytest.mark.real_llm
@pytest.mark.acceptance
class TestRealLLMEpicStoryTaskCreation:
    """Work item creation - ACCEPTANCE TESTS"""

    def test_create_epic_real_llm(self, real_orchestrator):
        """ACCEPTANCE: User can create epic with natural language"""
        project_id = real_orchestrator.state_manager.create_project("Test", "Test")

        # Various natural phrasings
        test_inputs = [
            "create epic for user authentication system",
            "I need an epic for user auth",
            "add an epic called user authentication"
        ]

        for user_input in test_inputs:
            result = real_orchestrator.execute_nl_command(user_input, project_id=project_id)

            assert result['success'], f"Failed for '{user_input}': {result.get('error')}"
            epic_id = result['data']['created_ids'][0]
            epic = real_orchestrator.state_manager.get_task(epic_id)
            assert epic.task_type == TaskType.EPIC
            assert "auth" in epic.title.lower()

    def test_create_story_real_llm(self, real_orchestrator):
        """ACCEPTANCE: User can create story"""
        project_id = real_orchestrator.state_manager.create_project("Test", "Test")
        epic_id = real_orchestrator.state_manager.create_epic(project_id, "Auth Epic", "Desc")

        result = real_orchestrator.execute_nl_command(
            f"add a story for password reset to epic {epic_id}",
            project_id=project_id
        )

        assert result['success']
        story_id = result['data']['created_ids'][0]
        story = real_orchestrator.state_manager.get_task(story_id)
        assert story.task_type == TaskType.STORY
        assert story.epic_id == epic_id

    def test_create_task_real_llm(self, real_orchestrator):
        """ACCEPTANCE: User can create task"""
        project_id = real_orchestrator.state_manager.create_project("Test", "Test")

        result = real_orchestrator.execute_nl_command(
            "create a task for implementing the login form",
            project_id=project_id
        )

        assert result['success']
        task_id = result['data']['created_ids'][0]
        task = real_orchestrator.state_manager.get_task(task_id)
        assert task.task_type == TaskType.TASK


@pytest.mark.requires_ollama
@pytest.mark.real_llm
@pytest.mark.acceptance
class TestRealLLMModificationWorkflows:
    """Update/delete workflows - ACCEPTANCE TESTS"""

    def test_update_task_status_real_llm(self, real_orchestrator):
        """ACCEPTANCE: User can update task status"""
        project_id = real_orchestrator.state_manager.create_project("Test", "Test")
        task_id = real_orchestrator.state_manager.create_task(
            project_id,
            {'title': 'Test Task', 'status': TaskStatus.PENDING}
        )

        result = real_orchestrator.execute_nl_command(
            f"mark task {task_id} as completed",
            project_id=project_id
        )

        assert result['success']
        task = real_orchestrator.state_manager.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_delete_task_real_llm(self, real_orchestrator):
        """ACCEPTANCE: User can delete tasks"""
        project_id = real_orchestrator.state_manager.create_project("Test", "Test")
        task_id = real_orchestrator.state_manager.create_task(project_id, {'title': 'To Delete'})

        result = real_orchestrator.execute_nl_command(
            f"delete task {task_id}",
            project_id=project_id
        )

        # Note: May require confirmation in real workflow
        assert result['success'] or 'confirm' in result['message'].lower()


# ... Add 15 more real LLM tests to reach 20 total

```

**Run Tests**:
```bash
# Check if Ollama is running
curl http://10.0.75.1:11434/api/tags

# Run acceptance tests
pytest tests/integration/test_nl_workflows_real_llm.py -v -m "real_llm and acceptance"

# Expected: 20/20 passing (or skipped if Ollama down)
```

**Commit**:
```bash
git add tests/conftest.py tests/integration/test_nl_workflows_real_llm.py
git commit -m "feat: Add REAL LLM acceptance tests (Phase 2)

- Added 20 acceptance tests with REAL Qwen 2.5 Coder LLM
- Uses actual Ollama endpoint (not mocks)
- Validates complete user workflows end-to-end
- Tests use natural language variations

⭐ PHASE 2 COMPLETE: Work is 'DONE' when these pass ⭐"
```

---

## PHASE 3: Automated Variation Testing (16 hours) 🚀

### Task 3.1: Variation Generator (4 hours)

**File**: `tests/utils/variation_generator.py` (CREATE NEW)

```python
"""Generate natural language variations for stress testing."""

from typing import List, Dict
import random
import itertools


class NLVariationGenerator:
    """Generate 100+ variations of NL commands for stress testing."""

    # Comprehensive variation templates
    VARIATION_TEMPLATES = {
        'create_epic': [
            # Direct imperatives
            "create epic for {topic}",
            "add an epic for {topic}",
            "make a new epic about {topic}",
            "new epic: {topic}",

            # Polite requests
            "can you create an epic for {topic}",
            "please add epic for {topic}",
            "I'd like to create an epic for {topic}",
            "would you create an epic called {topic}",

            # Conversational
            "I need an epic for {topic}",
            "I want to create an epic about {topic}",
            "let's add an epic for {topic}",
            "could we create an epic for {topic}",

            # Formal
            "create a new epic titled {topic}",
            "add epic with title {topic}",
            "establish epic for {topic}",

            # Casual
            "epic for {topic}",
            "new {topic} epic",
            "{topic} epic please",

            # With extra context
            "create epic for {topic} system",
            "add epic for {topic} feature",
            "make epic: {topic} implementation",

            # ... 80+ more variations
        ],

        'list_projects': [
            # Direct
            "list all projects",
            "show me all projects",
            "display all projects",
            "show projects",
            "list projects",

            # Questions
            "what projects do I have",
            "what are my projects",
            "which projects exist",
            "can you show me the projects",

            # Conversational
            "I want to see all projects",
            "show me what projects I have",
            "let me see all projects",

            # Variations
            "list every project",
            "show all available projects",
            "display my projects",

            # ... 80+ more variations
        ],

        # ... Templates for all 20 operations
    }

    def generate_variations(
        self,
        operation: str,
        count: int = 100,
        **kwargs
    ) -> List[str]:
        """Generate N variations of an operation.

        Args:
            operation: Operation type (e.g., 'create_epic', 'list_projects')
            count: Number of variations (default 100)
            **kwargs: Template parameters (e.g., topic="user auth")

        Returns:
            List of variation strings
        """
        templates = self.VARIATION_TEMPLATES.get(operation, [])

        if not templates:
            raise ValueError(f"No templates for operation: {operation}")

        variations = []

        # Use all templates if count <= template count
        if count <= len(templates):
            selected_templates = random.sample(templates, count)
            for template in selected_templates:
                variations.append(template.format(**kwargs))

        else:
            # Generate permutations if count > templates
            variations = self._generate_permutations(
                templates, kwargs, count
            )

        return variations[:count]  # Ensure exact count

    def _generate_permutations(
        self,
        templates: List[str],
        params: Dict,
        count: int
    ) -> List[str]:
        """Generate permutations by varying parameters."""
        variations = []

        # Use all templates first
        for template in templates:
            variations.append(template.format(**params))

        # If need more, vary parameters
        if len(variations) < count:
            param_variations = self._create_parameter_variations(params)

            for template, param_set in itertools.product(templates, param_variations):
                if len(variations) >= count:
                    break
                try:
                    variations.append(template.format(**param_set))
                except KeyError:
                    continue

        return variations

    def _create_parameter_variations(self, params: Dict) -> List[Dict]:
        """Create variations of parameters."""
        variations = [params.copy()]

        # Vary topic parameter
        if 'topic' in params:
            base_topic = params['topic']
            variations.extend([
                {**params, 'topic': f"{base_topic} system"},
                {**params, 'topic': f"{base_topic} feature"},
                {**params, 'topic': f"{base_topic} module"},
                {**params, 'topic': f"{base_topic} component"},
            ])

        return variations
```

**Verification**:
```python
# Quick test
python -c "
from tests.utils.variation_generator import NLVariationGenerator
gen = NLVariationGenerator()
variations = gen.generate_variations('create_epic', count=10, topic='user auth')
print(f'Generated {len(variations)} variations')
for i, v in enumerate(variations, 1):
    print(f'{i}. {v}')
"
```

### Task 3.2: Automated Test Runner (6 hours)

**File**: `tests/stress/automated_variation_tester.py` (CREATE NEW)

```python
"""Automated variation testing with self-documentation of failures."""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from tests.utils.variation_generator import NLVariationGenerator


class AutomatedVariationTester:
    """Run 100x variations and auto-document results."""

    def __init__(self, orchestrator, output_dir: Path):
        self.orchestrator = orchestrator
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.variation_generator = NLVariationGenerator()

    def run_variation_test(
        self,
        operation: str,
        count: int = 100,
        **params
    ) -> Dict[str, Any]:
        """Run N variations of an operation.

        Returns:
            {
                'operation': str,
                'total': int,
                'passed': int,
                'failed': int,
                'pass_rate': float,
                'failures': List[dict],
                'execution_time_ms': float
            }
        """
        start_time = time.time()

        variations = self.variation_generator.generate_variations(
            operation, count, **params
        )

        results = {
            'operation': operation,
            'total': count,
            'passed': 0,
            'failed': 0,
            'failures': [],
            'start_time': datetime.now().isoformat(),
            'parameters': params
        }

        print(f"\n{'='*60}")
        print(f"Testing: {operation} ({count} variations)")
        print(f"{'='*60}\n")

        for i, variation in enumerate(variations, 1):
            try:
                result = self.orchestrator.execute_nl_command(
                    variation,
                    project_id=params.get('project_id')
                )

                if result.get('success'):
                    results['passed'] += 1
                    print(f"  ✅ {i}/{count}: {variation[:50]}...")
                else:
                    results['failed'] += 1
                    results['failures'].append({
                        'variation': variation,
                        'error': result.get('error', result.get('message', 'Unknown')),
                        'iteration': i
                    })
                    print(f"  ❌ {i}/{count}: {variation[:50]}... - {result.get('error')}")

            except Exception as e:
                results['failed'] += 1
                results['failures'].append({
                    'variation': variation,
                    'exception': str(e),
                    'iteration': i
                })
                print(f"  ❌ {i}/{count}: {variation[:50]}... - Exception: {e}")

        execution_time = (time.time() - start_time) * 1000
        results['execution_time_ms'] = execution_time
        results['pass_rate'] = results['passed'] / results['total']

        print(f"\n{'='*60}")
        print(f"Results: {results['passed']}/{results['total']} passed ({results['pass_rate']:.1%})")
        print(f"Time: {execution_time/1000:.1f}s")
        print(f"{'='*60}\n")

        # Save results
        self._save_results(operation, results)

        # Auto-generate issue report if failures
        if results['failed'] > 0:
            self._generate_issue_report(operation, results)

        return results

    def _save_results(self, operation: str, results: dict):
        """Save test results to JSON."""
        output_file = self.output_dir / f"{operation}_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📊 Results saved: {output_file}")

    def _generate_issue_report(self, operation: str, results: dict):
        """Auto-generate issue report for failures."""
        report_path = self.output_dir / f"{operation}_ISSUES.md"

        with open(report_path, 'w') as f:
            f.write(f"# Variation Testing Issues: {operation}\n\n")
            f.write(f"**Date**: {results['start_time']}\n")
            f.write(f"**Total Variations**: {results['total']}\n")
            f.write(f"**Passed**: {results['passed']}\n")
            f.write(f"**Failed**: {results['failed']}\n")
            f.write(f"**Pass Rate**: {results['pass_rate']:.1%}\n\n")

            if results['failed'] > 0:
                f.write("## ❌ Status: BELOW 95% THRESHOLD\n\n")
                f.write("Requires fixes before proceeding.\n\n")

            f.write("---\n\n")
            f.write("## Failed Variations\n\n")

            for failure in results['failures']:
                f.write(f"### Iteration {failure['iteration']}\n\n")
                f.write(f"**Input**: `{failure['variation']}`\n\n")
                f.write(f"**Error**: {failure.get('error', failure.get('exception'))}\n\n")
                f.write("---\n\n")

            f.write("## Recommended Fixes\n\n")
            f.write(self._suggest_fixes(results['failures']))

        print(f"📝 Issue report: {report_path}")

    def _suggest_fixes(self, failures: List[dict]) -> str:
        """Group failures and suggest fixes."""
        # Group by error type
        error_groups = {}
        for failure in failures:
            error = failure.get('error', failure.get('exception', 'Unknown'))
            error_type = error.split(':')[0] if ':' in error else error

            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(failure['variation'])

        suggestions = []
        for error_type, examples in error_groups.items():
            suggestions.append(f"### Error Pattern: `{error_type}`\n")
            suggestions.append(f"**Affected variations**: {len(examples)}\n\n")
            suggestions.append("**Examples**:\n")
            for ex in examples[:3]:
                suggestions.append(f"- `{ex}`\n")
            suggestions.append(f"\n**Suggested Fix**: [Requires analysis]\n\n")
            suggestions.append("---\n\n")

        return "\n".join(suggestions)
```

### Task 3.3: Stress Test Suite (6 hours)

**File**: `tests/stress/test_automated_variations.py` (CREATE NEW)

```python
"""100x variation stress tests for all workflows.

These tests validate the NL pipeline handles natural language flexibility.
Acceptance: 95%+ pass rate for each workflow.
"""

import pytest
from pathlib import Path

from tests.stress.automated_variation_tester import AutomatedVariationTester


@pytest.fixture
def variation_tester(real_orchestrator, tmp_path):
    """Automated variation tester with real orchestrator."""
    return AutomatedVariationTester(real_orchestrator, tmp_path)


@pytest.mark.stress_test
@pytest.mark.requires_ollama
@pytest.mark.slow
class TestAutomatedVariations:
    """100x variations with REAL LLM - Final acceptance."""

    def test_create_epic_100_variations(self, variation_tester, real_orchestrator):
        """Stress test: Create epic with 100 natural variations.

        Acceptance: 95%+ success rate
        """
        project_id = real_orchestrator.state_manager.create_project("Test", "Test")

        results = variation_tester.run_variation_test(
            operation='create_epic',
            count=100,
            project_id=project_id,
            topic='user authentication'
        )

        # Acceptance criteria: 95% success rate
        pass_rate = results['pass_rate']
        assert pass_rate >= 0.95, \
            f"Pass rate {pass_rate:.1%} below 95% threshold. " \
            f"See {variation_tester.output_dir}/create_epic_ISSUES.md"

    def test_list_projects_100_variations(self, variation_tester, real_orchestrator):
        """Stress test: List projects with 100 natural variations."""
        # Create test projects
        for i in range(3):
            real_orchestrator.state_manager.create_project(f"Project {i}", "desc")

        results = variation_tester.run_variation_test(
            operation='list_projects',
            count=100,
            project_id=1
        )

        pass_rate = results['pass_rate']
        assert pass_rate >= 0.95, f"Pass rate {pass_rate:.1%} below 95%"

    # ... Add 18 more 100x variation tests (one per workflow) ...
```

**Run Tests**:
```bash
# Run single stress test (slow!)
pytest tests/stress/test_automated_variations.py::TestAutomatedVariations::test_create_epic_100_variations -v -s

# Run all stress tests (very slow - 30-60 minutes)
pytest tests/stress/test_automated_variations.py -v -s -m stress_test

# Check results
ls -la test_results/
cat test_results/create_epic_ISSUES.md  # If failures occurred
```

**Commit**:
```bash
git add tests/utils/variation_generator.py tests/stress/
git commit -m "feat: Add automated 100x variation testing (Phase 3)

- Variation generator with 100+ templates per operation
- Automated test runner with self-documentation
- 20 stress tests (100x variations each = 2000 total)
- Auto-generates issue reports for failures
- Acceptance: 95%+ pass rate

🚀 PHASE 3 COMPLETE: Automated stress testing infrastructure"
```

---

## PHASE 4: Automated Fix Loop (16 hours) 🤖

[Continues with automated fix infrastructure...]

---

## Quick Reference

### Test Execution

```bash
# PHASE 0: Fix broken tests
pytest tests/integration/test_orchestrator_nl_integration.py tests/smoke/test_smoke_workflows.py -v

# PHASE 1: Real component integration
pytest tests/integration/test_nl_workflows_real_components.py -v

# PHASE 2: Real LLM acceptance (⭐ "DONE" criteria)
pytest tests/integration/test_nl_workflows_real_llm.py -v -m "real_llm and acceptance"

# PHASE 3: 100x variation stress tests
pytest tests/stress/test_automated_variations.py -v -s -m stress_test

# Run specific workflow
pytest tests/integration/test_nl_workflows_real_llm.py::TestRealLLMEpicStoryTaskCreation::test_create_epic_real_llm -vv
```

### Check Progress

```bash
# How many tests pass?
pytest --co -q | grep "test session"

# What's coverage?
pytest --cov=src/nl --cov-report=term-missing

# Any stress test failures?
ls test_results/*_ISSUES.md 2>/dev/null || echo "No failures!"
```

---

**Status**: Ready for Autonomous Execution
**Estimated Timeline**: 10 days (80 hours)
**Philosophy**: ✅ REAL First, 🔶 Mocks Secondary
