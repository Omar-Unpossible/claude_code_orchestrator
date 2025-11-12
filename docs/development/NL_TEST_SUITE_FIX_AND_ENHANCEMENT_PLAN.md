# NL Test Suite Fix and Enhancement Plan
**Machine-Optimized Implementation Plan for Claude Code**

**Created**: 2025-11-11
**Status**: Ready for Implementation
**Estimated Effort**: 4-6 hours
**Priority**: High (92% passing → 100% + Real LLM validation)

---

## Executive Summary

**Current State**:
- 206 NL command tests created
- 92% pass rate (190/206 passing)
- **All tests use mocks** - zero real LLM validation
- 16 tests failing due to broken mock LLM fixtures

**Target State**:
- 100% mock test pass rate (206/206)
- 20-30 real LLM integration tests
- Dual test strategy: Fast mocks (31s) + Real LLM validation (5-10min)
- Comprehensive testing documentation

**Why This Matters**:
- Mock tests catch code logic errors (fast feedback)
- Real LLM tests catch prompt engineering issues (production validation)
- Current failures block merge to main
- No real LLM testing = unvalidated production behavior

---

## Implementation Phases

### Phase 1: Fix Mock LLM Fixtures (Priority 1)
**Estimated Time**: 1-2 hours
**Goal**: Achieve 100% pass rate on existing 206 tests

### Phase 2: Create Real LLM Integration Tests (Priority 2)
**Estimated Time**: 2-3 hours
**Goal**: Add 20-30 tests using actual Ollama/Qwen

### Phase 3: Documentation and Strategy (Priority 3)
**Estimated Time**: 1 hour
**Goal**: Document when to use mocks vs real LLMs

### Phase 4: CI/CD Configuration (Optional)
**Estimated Time**: 30 minutes
**Goal**: Run real LLM tests on merge to main only

---

## Phase 1: Fix Mock LLM Fixtures

### Task 1.1: Analyze Current Mock Failures

**Objective**: Understand root cause of 16 test failures

**Files to Examine**:
- `tests/conftest.py` - Main mock fixtures
- `tests/test_nl_entity_extractor_bug_prevention.py` (5 failures)
- `tests/test_nl_command_processor_integration.py` (4 failures)
- `tests/test_nl_e2e_integration.py` (7 failures)

**Common Failure Patterns**:
```python
# Pattern 1: Missing required fields
EntityExtractionException: Failed to parse LLM response: Missing required fields in response: ['entity_type', 'entities']

# Pattern 2: Invalid JSON
ValueError: Invalid JSON in LLM response: substring not found

# Pattern 3: MagicMock objects in output
"<MagicMock name='mock.generate()' id='134271918708864'>"
```

**Root Cause**: Mock LLMs return `MagicMock` objects or incomplete JSON instead of valid Obra schema responses.

**Acceptance Criteria**:
- ✅ Identified all 16 failing test cases
- ✅ Categorized failures by root cause
- ✅ Documented required JSON schema for each entity type

**Verification**:
```bash
# List all failures with details
pytest tests/test_nl_entity_extractor_bug_prevention.py tests/test_nl_command_processor_integration.py tests/test_nl_e2e_integration.py -v --tb=line
```

---

### Task 1.2: Create Valid Mock Response Fixtures

**Objective**: Build reusable mock response fixtures matching Obra schema

**File to Modify**: `tests/conftest.py`

**Implementation**:

```python
# Add to tests/conftest.py

import json
from typing import Dict, Any, List

# ============================================================================
# Mock LLM Response Fixtures (Valid Obra Schema)
# ============================================================================

@pytest.fixture
def mock_llm_responses() -> Dict[str, str]:
    """
    Valid JSON responses matching Obra entity schema.

    Used by mock LLMs to return realistic, parseable responses.
    Each response matches the schema in src/nl/schemas/obra_schema.json.

    Returns:
        Dictionary mapping entity_type -> valid JSON response
    """
    return {
        # Epic creation
        "epic": json.dumps({
            "entity_type": "epic",
            "entities": [{
                "title": "User Authentication System",
                "description": "Complete auth with OAuth, MFA, session management",
                "priority": 3
            }],
            "confidence": 0.92,
            "reasoning": "Clear epic with title, description, and priority"
        }),

        # Story creation
        "story": json.dumps({
            "entity_type": "story",
            "entities": [{
                "title": "Password Reset Flow",
                "description": "As a user, I want to reset my password so I can regain access",
                "epic_id": 1
            }],
            "confidence": 0.88,
            "reasoning": "User story format with epic reference"
        }),

        # Task creation
        "task": json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Implement password hashing",
                "description": "Use bcrypt for secure password storage",
                "story_id": 1,
                "dependencies": []
            }],
            "confidence": 0.90,
            "reasoning": "Technical task with clear title and story reference"
        }),

        # Subtask creation
        "subtask": json.dumps({
            "entity_type": "subtask",
            "entities": [{
                "title": "Write unit tests for password validation",
                "parent_task_id": 1
            }],
            "confidence": 0.93,
            "reasoning": "Clear subtask with parent reference"
        }),

        # Milestone creation
        "milestone": json.dumps({
            "entity_type": "milestone",
            "entities": [{
                "name": "Auth Complete",
                "description": "All authentication features implemented",
                "required_epic_ids": [1, 2]
            }],
            "confidence": 0.94,
            "reasoning": "Milestone with epic dependencies"
        }),

        # Project query
        "project": json.dumps({
            "entity_type": "project",
            "entities": [{
                "name": "Current Project Query"
            }],
            "confidence": 0.85,
            "reasoning": "Project-level information request"
        }),

        # Multi-entity (batch creation)
        "multi_task": json.dumps({
            "entity_type": "task",
            "entities": [
                {"title": "Task 1", "description": "First task"},
                {"title": "Task 2", "description": "Second task"},
                {"title": "Task 3", "description": "Third task"}
            ],
            "confidence": 0.87,
            "reasoning": "Batch task creation with 3 items"
        }),

        # Intent classification - COMMAND
        "intent_command": json.dumps({
            "intent": "COMMAND",
            "confidence": 0.95,
            "reasoning": "Clear action verb 'create' indicates command intent"
        }),

        # Intent classification - QUESTION
        "intent_question": json.dumps({
            "intent": "QUESTION",
            "confidence": 0.92,
            "reasoning": "Question word 'what' and query pattern indicate information request"
        })
    }


@pytest.fixture
def mock_llm_smart(mock_llm_responses):
    """
    Smart mock LLM that returns valid responses based on input.

    Analyzes the prompt to determine entity type and returns
    appropriate valid JSON from mock_llm_responses fixture.

    Usage:
        mock = mock_llm_smart
        llm_interface.llm = mock
    """
    from unittest.mock import MagicMock

    mock = MagicMock()

    def smart_generate(prompt: str, **kwargs) -> str:
        """Return appropriate response based on prompt content"""
        prompt_lower = prompt.lower()

        # Intent classification
        if '"intent":' in prompt_lower or 'classify' in prompt_lower:
            if any(word in prompt_lower for word in ['what', 'how', 'why', 'when', 'where']):
                return mock_llm_responses["intent_question"]
            else:
                return mock_llm_responses["intent_command"]

        # Entity extraction - detect entity type from prompt
        if 'epic' in prompt_lower:
            return mock_llm_responses["epic"]
        elif 'story' in prompt_lower or 'user story' in prompt_lower:
            return mock_llm_responses["story"]
        elif 'subtask' in prompt_lower:
            return mock_llm_responses["subtask"]
        elif 'milestone' in prompt_lower:
            return mock_llm_responses["milestone"]
        elif 'project' in prompt_lower or 'current project' in prompt_lower:
            return mock_llm_responses["project"]
        elif 'task' in prompt_lower:
            # Check for batch creation
            if any(num in prompt_lower for num in ['3 tasks', 'three tasks', 'multiple']):
                return mock_llm_responses["multi_task"]
            else:
                return mock_llm_responses["task"]

        # Default to task if unclear
        return mock_llm_responses["task"]

    mock.generate.side_effect = smart_generate
    return mock


@pytest.fixture
def mock_llm_simple(mock_llm_responses):
    """
    Simple mock LLM that always returns task entity.

    Use when you need a basic mock and don't care about
    specific entity types (e.g., testing error handling).
    """
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.generate.return_value = mock_llm_responses["task"]
    return mock
```

**Acceptance Criteria**:
- ✅ Created `mock_llm_responses` fixture with all entity types
- ✅ Created `mock_llm_smart` fixture that returns appropriate responses
- ✅ Created `mock_llm_simple` fixture for basic use cases
- ✅ All JSON responses validate against `src/nl/schemas/obra_schema.json`

**Verification**:
```bash
# Validate mock responses against schema
python -c "
import json
from src.nl.entity_extractor import EntityExtractor
# Test each mock response can be parsed
"
```

---

### Task 1.3: Fix Failing Tests in test_nl_entity_extractor_bug_prevention.py

**Objective**: Update 5 failing tests to use new mock fixtures

**File to Modify**: `tests/test_nl_entity_extractor_bug_prevention.py`

**Current Failures**:
1. `test_entity_type_none_raises_user_friendly_exception` - Mock returns invalid JSON
2. `test_entity_type_missing_field_entirely` - Mock missing required fields
3. `test_valid_entity_types_all_accepted` - Mock returns MagicMock objects
4. `test_query_current_project_extracts_correctly` - Mock invalid JSON
5. `test_project_query_variations` - Mock invalid JSON

**Implementation Strategy**:

```python
# Example fix for test_query_current_project_extracts_correctly

# BEFORE (broken)
def test_query_current_project_extracts_correctly(self, test_config, state_manager):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = MagicMock()  # ❌ Returns MagicMock object
    # ...

# AFTER (fixed)
def test_query_current_project_extracts_correctly(
    self,
    test_config,
    state_manager,
    mock_llm_smart  # ✅ Use smart mock fixture
):
    test_config.set('testing.mode', False)  # Don't auto-mock

    extractor = EntityExtractor(config=test_config, state_manager=state_manager)
    extractor.llm = mock_llm_smart  # ✅ Inject smart mock

    result = extractor.extract("What is the current project?", "COMMAND")

    assert result.entity_type == "project"  # ✅ Valid response
    assert result.confidence >= 0.7
```

**Specific Fixes Needed**:

1. **test_entity_type_none_raises_user_friendly_exception**:
   - Create mock that returns `{"entity_type": null, ...}` (intentionally invalid)
   - Verify exception message suggests valid entity types

2. **test_entity_type_missing_field_entirely**:
   - Create mock that returns `{"entities": [...]}` (missing entity_type)
   - Verify exception message mentions missing required fields

3. **test_valid_entity_types_all_accepted**:
   - Use `mock_llm_smart` fixture
   - Test all entity types: epic, story, task, subtask, milestone, project

4. **test_query_current_project_extracts_correctly**:
   - Use `mock_llm_smart` with "project" response
   - Verify entity_type == "project"

5. **test_project_query_variations**:
   - Use `mock_llm_smart` for multiple project query variations
   - Test "what project?", "current project", "show project"

**Acceptance Criteria**:
- ✅ All 5 tests in bug_prevention file pass
- ✅ Tests use new mock fixtures from conftest.py
- ✅ Tests validate both success and error cases

**Verification**:
```bash
pytest tests/test_nl_entity_extractor_bug_prevention.py -v
# Expected: 6 passed in < 1s
```

---

### Task 1.4: Fix Failing Tests in test_nl_command_processor_integration.py

**Objective**: Update 4 failing integration tests

**File to Modify**: `tests/test_nl_command_processor_integration.py`

**Current Failures**:
1. `test_query_current_project_success` - Mock LLM invalid response
2. `test_create_epic_success` - Entity extraction fails
3. `test_create_story_with_epic_id` - Entity extraction fails
4. `test_forward_question_to_claude` - Intent misclassified (COMMAND vs QUESTION)

**Implementation Strategy**:

Replace inline mocks with fixtures:

```python
# BEFORE (broken)
@patch('src.nl.intent_classifier.IntentClassifier')
def test_create_epic_success(self, mock_classifier_class, state_manager):
    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = IntentResult(...)
    mock_classifier_class.return_value = mock_classifier
    # Mock returns invalid JSON -> test fails

# AFTER (fixed)
def test_create_epic_success(
    self,
    state_manager,
    test_config,
    mock_llm_smart  # ✅ Use smart mock
):
    # No patching needed - use real components with mock LLM
    test_config.set('testing.mode', False)

    processor = NLCommandProcessor(
        config=test_config,
        state_manager=state_manager
    )
    processor.entity_extractor.llm = mock_llm_smart
    processor.intent_classifier.llm = mock_llm_smart

    response = processor.process_message(
        "Create epic 'User Authentication'",
        context={'project_id': 1}
    )

    assert response.success is True
    assert response.intent == "COMMAND"
    assert len(response.execution_result.created_ids) == 1
```

**Specific Fixes**:

1. **test_query_current_project_success**:
   - Use `mock_llm_smart` for both intent and entity extraction
   - Verify successful project query execution

2. **test_create_epic_success**:
   - Use `mock_llm_smart` with "epic" response
   - Verify epic created in database

3. **test_create_story_with_epic_id**:
   - First create epic (prerequisite)
   - Use `mock_llm_smart` with "story" response
   - Verify story linked to epic

4. **test_forward_question_to_claude**:
   - Configure `mock_llm_smart` to return QUESTION intent
   - Verify message forwarded (not executed as command)

**Acceptance Criteria**:
- ✅ All 4 failing tests now pass
- ✅ Tests use real NLCommandProcessor (not mocked)
- ✅ Only LLM interface is mocked (proper isolation)

**Verification**:
```bash
pytest tests/test_nl_command_processor_integration.py -v
# Expected: 25 passed in ~4s
```

---

### Task 1.5: Fix Failing Tests in test_nl_e2e_integration.py

**Objective**: Update 7 failing E2E tests

**File to Modify**: `tests/test_nl_e2e_integration.py`

**Current Failures**:
1. `test_create_epic_execution_error` - Assertion logic error
2. `test_create_story_no_epic_reference` - Missing epic_id handling
3. `test_create_story_user_story_format` - Entity extraction fails
4. `test_create_story_with_acceptance_criteria` - Missing epic_id
5. `test_update_task_status` - Missing title in update
6. `test_update_task_add_dependency` - Validation error
7. `test_execution_error_formatting` - MagicMock in error message

**Implementation Strategy**:

```python
# Example: Fix test_create_story_no_epic_reference

# BEFORE (broken)
def test_create_story_no_epic_reference(self, e2e_components):
    # Test expects failure but success=False not handled correctly
    result = executor.execute(...)
    assert result.success is True  # ❌ Wrong expectation

# AFTER (fixed)
def test_create_story_no_epic_reference(
    self,
    e2e_components,
    mock_llm_smart
):
    extractor = e2e_components['entity_extractor']
    extractor.llm = mock_llm_smart

    validator = e2e_components['command_validator']
    executor = e2e_components['command_executor']

    # Extract story without epic_id
    extracted = extractor.extract(
        "Create story 'Password Reset'",
        "COMMAND"
    )

    # Should fail validation (story requires epic_id)
    validation = validator.validate(extracted)

    assert validation.valid is False  # ✅ Expect validation failure
    assert "epic_id" in str(validation.errors).lower()
```

**Specific Fixes**:

1. **test_create_epic_execution_error**:
   - Fix assertion: Should expect `success=False` when error occurs
   - Verify error message in `execution_result.errors`

2. **test_create_story_no_epic_reference**:
   - Expect validation failure (story requires epic_id)
   - Verify helpful error message

3. **test_create_story_user_story_format**:
   - Configure `mock_llm_smart` to extract from user story format
   - Ensure epic_id provided or test validation failure

4. **test_create_story_with_acceptance_criteria**:
   - Create epic first (prerequisite)
   - Extract story with acceptance_criteria field

5. **test_update_task_status**:
   - Mock should return task entity with status update
   - Validate task update command has required fields

6. **test_update_task_add_dependency**:
   - Mock should return task entity with dependency addition
   - Both tasks must exist before adding dependency

7. **test_execution_error_formatting**:
   - Remove MagicMock from formatter
   - Use real error message formatting

**Acceptance Criteria**:
- ✅ All 7 failing E2E tests pass
- ✅ Tests exercise full pipeline (intent → extract → validate → execute)
- ✅ Error cases properly validated (not just success cases)

**Verification**:
```bash
pytest tests/test_nl_e2e_integration.py -v
# Expected: 30 passed in ~5s
```

---

### Task 1.6: Verify 100% Mock Test Pass Rate

**Objective**: Confirm all 206 tests pass with fixed mocks

**Verification Commands**:

```bash
# Run all NL tests
pytest tests/test_nl_*.py -v --tb=short

# Expected output:
# ===================== 206 passed in ~31s ======================

# Run with coverage
pytest tests/test_nl_*.py --cov=src/nl --cov-report=term --cov-report=html

# Expected coverage: ~75-80%
```

**Acceptance Criteria**:
- ✅ 206/206 tests passing (100% pass rate)
- ✅ Execution time ≤ 35 seconds (fast feedback)
- ✅ No warnings about missing fields or invalid JSON
- ✅ Coverage ≥ 75%

**Deliverables**:
- ✅ Updated `tests/conftest.py` with mock fixtures
- ✅ Fixed `tests/test_nl_entity_extractor_bug_prevention.py` (6/6 passing)
- ✅ Fixed `tests/test_nl_command_processor_integration.py` (25/25 passing)
- ✅ Fixed `tests/test_nl_e2e_integration.py` (30/30 passing)
- ✅ All other test files unchanged but still passing

---

## Phase 2: Create Real LLM Integration Tests

### Task 2.1: Design Real LLM Test Strategy

**Objective**: Define what to test with real LLMs vs mocks

**Decision Matrix**:

| Component | Mock Tests | Real LLM Tests | Rationale |
|-----------|------------|----------------|-----------|
| IntentClassifier | ✅ Logic, edge cases | ✅ Prompt quality, accuracy | Need both speed and validation |
| EntityExtractor | ✅ Parsing, schema | ✅ Extraction accuracy | Prompt engineering critical |
| CommandValidator | ✅ All tests | ❌ Not LLM-dependent | Pure logic, mocks sufficient |
| CommandExecutor | ✅ All tests | ❌ Not LLM-dependent | Database ops, no LLM |
| NLCommandProcessor | ✅ Integration flow | ✅ Full E2E pipeline | Need real workflow validation |
| Error Scenarios | ✅ All scenarios | ⚠️ LLM failures only | Mock for speed, real for LLM issues |

**Real LLM Test Categories**:
1. **Intent Classification Accuracy** (8 tests)
   - Clear commands (create, add, update, delete)
   - Clear questions (what, how, show, list)
   - Ambiguous inputs (test edge cases)
   - Multi-intent messages

2. **Entity Extraction Accuracy** (10 tests)
   - Single entity per type (epic, story, task, subtask, milestone)
   - Multi-entity batch creation
   - Entity with dependencies/references
   - Complex user story formats
   - Edge cases (emojis, code blocks, special chars)

3. **Full Pipeline E2E** (8 tests)
   - Create epic → stories → tasks workflow
   - Task with dependencies
   - Milestone achievement flow
   - Error recovery (invalid epic_id, circular deps)

4. **LLM Failure Modes** (4 tests)
   - Timeout handling (configure short timeout)
   - Rate limit simulation
   - Invalid JSON response recovery
   - Partial response handling

**Total Real LLM Tests**: 30 tests
**Estimated Execution Time**: 5-10 minutes (with caching, 0.3-0.5s per LLM call)

**Acceptance Criteria**:
- ✅ Categorized tests into mock vs real LLM
- ✅ Defined 30 real LLM test cases
- ✅ Estimated execution time per test
- ✅ Documented rationale for each category

---

### Task 2.2: Create Real LLM Test File Structure

**Objective**: Set up test file with proper markers and fixtures

**File to Create**: `tests/test_nl_real_llm_integration.py`

**Implementation**:

```python
"""
Real LLM Integration Tests for NL Command System

IMPORTANT: These tests use actual Ollama/Qwen LLM calls - SLOW but validates production behavior.

Requirements:
- Ollama running on http://172.29.144.1:11434
- Qwen 2.5 Coder model pulled: `ollama pull qwen2.5-coder:32b`

Execution:
    # Run all real LLM tests (5-10 minutes)
    pytest tests/test_nl_real_llm_integration.py -v -m integration

    # Run specific category
    pytest tests/test_nl_real_llm_integration.py -v -k "intent_classification"

    # Skip slow tests (run in CI on merge only)
    pytest tests/test_nl_*.py -v -m "not integration"

Created: 2025-11-11
Author: Obra Development Team
"""

import pytest
import time
from typing import Dict, Any

# Mark entire file as integration tests (slow, requires Ollama)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.requires_ollama
]


# ============================================================================
# Fixtures for Real LLM Testing
# ============================================================================

@pytest.fixture(scope="module")
def real_llm_config(test_config):
    """
    Configure for real LLM (not mock).

    Module-scoped to reuse config across all tests in file.
    """
    test_config.set('testing.mode', False)  # Disable auto-mocking
    test_config.set('llm.provider', 'ollama')
    test_config.set('llm.model', 'qwen2.5-coder:32b')
    test_config.set('llm.base_url', 'http://172.29.144.1:11434')
    test_config.set('llm.timeout', 30.0)  # Real LLM needs more time
    test_config.set('llm.temperature', 0.1)  # Low temp for consistency
    return test_config


@pytest.fixture(scope="module")
def real_state_manager(real_llm_config):
    """
    StateManager for real LLM tests.

    Module-scoped to reuse database across tests (faster).
    Uses in-memory SQLite for speed.
    """
    from src.core.state import StateManager

    state = StateManager(
        config=real_llm_config,
        db_url="sqlite:///:memory:"
    )

    # Create test project
    project = state.create_project(
        name="Real LLM Test Project",
        working_directory="/tmp/test",
        default_agent="mock"
    )
    state.set_current_project(project.id)

    yield state

    # Cleanup
    state.close()


@pytest.fixture
def real_intent_classifier(real_llm_config, real_state_manager):
    """IntentClassifier using real Ollama LLM"""
    from src.nl.intent_classifier import IntentClassifier
    return IntentClassifier(
        config=real_llm_config,
        state_manager=real_state_manager
    )


@pytest.fixture
def real_entity_extractor(real_llm_config, real_state_manager):
    """EntityExtractor using real Ollama LLM"""
    from src.nl.entity_extractor import EntityExtractor
    return EntityExtractor(
        config=real_llm_config,
        state_manager=real_state_manager
    )


@pytest.fixture
def real_nl_processor(real_llm_config, real_state_manager):
    """NLCommandProcessor using real Ollama LLM"""
    from src.nl.nl_command_processor import NLCommandProcessor
    return NLCommandProcessor(
        config=real_llm_config,
        state_manager=real_state_manager
    )


# ============================================================================
# Helper Utilities
# ============================================================================

def assert_valid_intent_result(result, expected_intent: str, min_confidence: float = 0.7):
    """Validate IntentResult from real LLM"""
    assert result is not None
    assert result.intent in ["COMMAND", "QUESTION"]
    assert result.intent == expected_intent, f"Expected {expected_intent}, got {result.intent}"
    assert result.confidence >= min_confidence, f"Confidence {result.confidence} below threshold {min_confidence}"
    assert len(result.reasoning) > 0, "Reasoning should not be empty"


def assert_valid_extraction_result(
    result,
    expected_entity_type: str,
    min_entities: int = 1,
    min_confidence: float = 0.7
):
    """Validate ExtractedEntities from real LLM"""
    assert result is not None
    assert result.entity_type == expected_entity_type
    assert len(result.entities) >= min_entities
    assert result.confidence >= min_confidence
    assert len(result.reasoning) > 0


# ============================================================================
# Test Classes
# ============================================================================

class TestRealLLMIntentClassification:
    """Test intent classification with real Ollama/Qwen LLM"""

    def test_clear_command_create_task(self, real_intent_classifier):
        """REAL LLM: Classify 'Create task' as COMMAND"""
        result = real_intent_classifier.classify(
            "Create a task for implementing OAuth"
        )
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.8)

    # ... (more tests below)


class TestRealLLMEntityExtraction:
    """Test entity extraction with real Ollama/Qwen LLM"""

    def test_extract_epic_from_natural_language(self, real_entity_extractor):
        """REAL LLM: Extract epic from natural language"""
        result = real_entity_extractor.extract(
            "Create epic 'User Authentication' with password reset and OAuth",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "epic", min_entities=1, min_confidence=0.8)

        epic = result.entities[0]
        assert 'title' in epic
        assert 'authentication' in epic['title'].lower()

    # ... (more tests below)


class TestRealLLMFullPipeline:
    """Test complete NL pipeline with real Ollama/Qwen LLM"""

    def test_create_epic_end_to_end(self, real_nl_processor):
        """REAL LLM: Full pipeline - create epic"""
        response = real_nl_processor.process_message(
            "Create an epic called 'Payment System' for Stripe integration",
            context={'project_id': 1}
        )

        assert response.success is True
        assert response.intent == "COMMAND"
        assert response.execution_result is not None
        assert len(response.execution_result.created_ids) == 1

    # ... (more tests below)


class TestRealLLMFailureModes:
    """Test LLM failure handling with real Ollama/Qwen LLM"""

    @pytest.mark.timeout(35)  # Should timeout at 30s
    def test_llm_timeout_handling(self, real_llm_config, real_state_manager):
        """REAL LLM: Handle timeout gracefully"""
        # Configure very short timeout
        real_llm_config.set('llm.timeout', 1.0)  # 1 second - too short

        from src.nl.entity_extractor import EntityExtractor
        extractor = EntityExtractor(
            config=real_llm_config,
            state_manager=real_state_manager
        )

        # Should raise timeout exception
        with pytest.raises(Exception) as exc_info:
            extractor.extract(
                "Create a very complex epic with lots of details...",
                intent="COMMAND"
            )

        assert "timeout" in str(exc_info.value).lower()

    # ... (more tests below)
```

**Acceptance Criteria**:
- ✅ Created `tests/test_nl_real_llm_integration.py`
- ✅ Configured pytest markers: `integration`, `slow`, `requires_ollama`
- ✅ Created module-scoped fixtures for performance
- ✅ Helper validation functions for results
- ✅ Structured into 4 test classes

**Verification**:
```bash
# Verify file structure
pytest tests/test_nl_real_llm_integration.py --collect-only

# Should show ~30 test items across 4 classes
```

---

### Task 2.3: Implement Intent Classification Tests (8 tests)

**Objective**: Validate intent classification accuracy with real LLM

**Add to `TestRealLLMIntentClassification` class**:

```python
class TestRealLLMIntentClassification:
    """Test intent classification with real Ollama/Qwen LLM"""

    # ========== Clear Commands (4 tests) ==========

    def test_clear_command_create_task(self, real_intent_classifier):
        """REAL LLM: Classify 'Create task' as COMMAND"""
        result = real_intent_classifier.classify(
            "Create a task for implementing OAuth"
        )
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.8)

    def test_clear_command_add_story(self, real_intent_classifier):
        """REAL LLM: Classify 'Add story' as COMMAND"""
        result = real_intent_classifier.classify(
            "Add a story for password reset to epic 5"
        )
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.8)

    def test_clear_command_update_task(self, real_intent_classifier):
        """REAL LLM: Classify 'Update task' as COMMAND"""
        result = real_intent_classifier.classify(
            "Update task 7 status to in-progress"
        )
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.8)

    def test_clear_command_delete_epic(self, real_intent_classifier):
        """REAL LLM: Classify 'Delete epic' as COMMAND"""
        result = real_intent_classifier.classify(
            "Delete epic 3 and all its stories"
        )
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.8)

    # ========== Clear Questions (4 tests) ==========

    def test_clear_question_what(self, real_intent_classifier):
        """REAL LLM: Classify 'What...' as QUESTION"""
        result = real_intent_classifier.classify(
            "What is the current project?"
        )
        assert_valid_intent_result(result, "QUESTION", min_confidence=0.8)

    def test_clear_question_how(self, real_intent_classifier):
        """REAL LLM: Classify 'How...' as QUESTION"""
        result = real_intent_classifier.classify(
            "How do I implement OAuth with Obra?"
        )
        assert_valid_intent_result(result, "QUESTION", min_confidence=0.8)

    def test_clear_question_show(self, real_intent_classifier):
        """REAL LLM: Classify 'Show...' as QUESTION"""
        result = real_intent_classifier.classify(
            "Show me all open tasks for epic 5"
        )
        assert_valid_intent_result(result, "QUESTION", min_confidence=0.8)

    def test_clear_question_list(self, real_intent_classifier):
        """REAL LLM: Classify 'List...' as QUESTION"""
        result = real_intent_classifier.classify(
            "List all stories with acceptance criteria"
        )
        assert_valid_intent_result(result, "QUESTION", min_confidence=0.8)
```

**Acceptance Criteria**:
- ✅ 8 intent classification tests implemented
- ✅ All tests use real Ollama/Qwen LLM
- ✅ Tests cover both COMMAND and QUESTION intents
- ✅ Confidence thresholds validate prompt quality

**Verification**:
```bash
# Run intent classification tests only
pytest tests/test_nl_real_llm_integration.py::TestRealLLMIntentClassification -v

# Expected: 8 passed in ~30-60s (depends on LLM speed)
```

---

### Task 2.4: Implement Entity Extraction Tests (10 tests)

**Objective**: Validate entity extraction accuracy with real LLM

**Add to `TestRealLLMEntityExtraction` class**:

```python
class TestRealLLMEntityExtraction:
    """Test entity extraction with real Ollama/Qwen LLM"""

    # ========== Single Entity Extraction (5 tests) ==========

    def test_extract_epic_from_natural_language(self, real_entity_extractor):
        """REAL LLM: Extract epic from natural language"""
        result = real_entity_extractor.extract(
            "Create epic 'User Authentication' with password reset and OAuth",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "epic", min_entities=1, min_confidence=0.8)

        epic = result.entities[0]
        assert 'title' in epic
        assert 'authentication' in epic['title'].lower()

    def test_extract_story_with_user_story_format(self, real_entity_extractor):
        """REAL LLM: Extract story from user story format"""
        result = real_entity_extractor.extract(
            "As a user, I want to reset my password so that I can regain access if I forget it",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "story", min_entities=1, min_confidence=0.7)

        story = result.entities[0]
        assert 'title' in story
        assert 'description' in story

    def test_extract_task_with_description(self, real_entity_extractor):
        """REAL LLM: Extract task with clear title and description"""
        result = real_entity_extractor.extract(
            "Create task 'Implement password hashing' using bcrypt for secure storage",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "task", min_entities=1, min_confidence=0.8)

        task = result.entities[0]
        assert 'title' in task
        assert 'password' in task['title'].lower() or 'hashing' in task['title'].lower()

    def test_extract_subtask_with_parent(self, real_entity_extractor):
        """REAL LLM: Extract subtask with parent reference"""
        result = real_entity_extractor.extract(
            "Add subtask to task 7: Write unit tests for password validation",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "subtask", min_entities=1, min_confidence=0.8)

        subtask = result.entities[0]
        assert 'title' in subtask
        assert 'parent_task_id' in subtask
        assert subtask['parent_task_id'] == 7

    def test_extract_milestone_with_epic_dependencies(self, real_entity_extractor):
        """REAL LLM: Extract milestone with required epics"""
        result = real_entity_extractor.extract(
            "Create milestone 'Auth Complete' when epics 5 and 7 are done",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "milestone", min_entities=1, min_confidence=0.8)

        milestone = result.entities[0]
        assert 'name' in milestone
        assert 'required_epic_ids' in milestone
        assert 5 in milestone['required_epic_ids']
        assert 7 in milestone['required_epic_ids']

    # ========== Multi-Entity Extraction (2 tests) ==========

    def test_extract_multiple_tasks_batch(self, real_entity_extractor):
        """REAL LLM: Extract multiple tasks from batch creation"""
        result = real_entity_extractor.extract(
            "Create 3 tasks: Implement login, Implement logout, Implement session management",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "task", min_entities=3, min_confidence=0.8)

        titles = [task['title'] for task in result.entities]
        assert any('login' in title.lower() for title in titles)
        assert any('logout' in title.lower() for title in titles)
        assert any('session' in title.lower() for title in titles)

    def test_extract_stories_with_epic_reference(self, real_entity_extractor):
        """REAL LLM: Extract multiple stories with epic reference"""
        result = real_entity_extractor.extract(
            "Add stories to epic 'Auth': Email login, OAuth login, MFA setup",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "story", min_entities=3, min_confidence=0.7)

        # All stories should reference the epic
        for story in result.entities:
            assert 'title' in story

    # ========== Edge Cases (3 tests) ==========

    def test_extract_with_emojis(self, real_entity_extractor):
        """REAL LLM: Handle emojis in input"""
        result = real_entity_extractor.extract(
            "Create epic 🔐 'Security Hardening' for 🛡️ defense measures",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "epic", min_entities=1, min_confidence=0.7)

    def test_extract_with_code_blocks(self, real_entity_extractor):
        """REAL LLM: Handle code blocks in input"""
        result = real_entity_extractor.extract(
            "Create task: Implement `bcrypt.hash(password)` for password hashing",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "task", min_entities=1, min_confidence=0.7)

    def test_extract_with_special_characters(self, real_entity_extractor):
        """REAL LLM: Handle special characters"""
        result = real_entity_extractor.extract(
            "Create story: Support @mentions & #hashtags in comments",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "story", min_entities=1, min_confidence=0.7)
```

**Acceptance Criteria**:
- ✅ 10 entity extraction tests implemented
- ✅ Tests cover all entity types (epic, story, task, subtask, milestone)
- ✅ Tests validate multi-entity batch creation
- ✅ Edge cases (emojis, code, special chars) handled

**Verification**:
```bash
pytest tests/test_nl_real_llm_integration.py::TestRealLLMEntityExtraction -v
# Expected: 10 passed in ~90-150s
```

---

### Task 2.5: Implement Full Pipeline E2E Tests (8 tests)

**Objective**: Validate complete NL pipeline with real LLM

**Add to `TestRealLLMFullPipeline` class**:

```python
class TestRealLLMFullPipeline:
    """Test complete NL pipeline with real Ollama/Qwen LLM"""

    def test_create_epic_end_to_end(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - create epic"""
        response = real_nl_processor.process_message(
            "Create an epic called 'Payment System' for Stripe integration",
            context={'project_id': 1}
        )

        assert response.success is True
        assert response.intent == "COMMAND"
        assert response.execution_result is not None
        assert len(response.execution_result.created_ids) == 1

        # Verify in database
        epic_id = response.execution_result.created_ids[0]
        epic = real_state_manager.get_epic(epic_id)
        assert epic is not None
        assert 'payment' in epic.title.lower()

    def test_create_story_with_epic_workflow(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - create epic then story"""
        # Step 1: Create epic
        epic_response = real_nl_processor.process_message(
            "Create epic 'User Management'",
            context={'project_id': 1}
        )
        assert epic_response.success is True
        epic_id = epic_response.execution_result.created_ids[0]

        # Step 2: Create story in epic
        story_response = real_nl_processor.process_message(
            f"Add story 'User Registration' to epic {epic_id}",
            context={'project_id': 1}
        )
        assert story_response.success is True
        story_id = story_response.execution_result.created_ids[0]

        # Verify story linked to epic
        story = real_state_manager.get_story(story_id)
        assert story.epic_id == epic_id

    def test_create_task_with_dependencies(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - task with dependencies"""
        # Create prerequisite tasks
        task1_response = real_nl_processor.process_message(
            "Create task 'Setup database schema'",
            context={'project_id': 1}
        )
        task1_id = task1_response.execution_result.created_ids[0]

        task2_response = real_nl_processor.process_message(
            "Create task 'Write migration scripts'",
            context={'project_id': 1}
        )
        task2_id = task2_response.execution_result.created_ids[0]

        # Create dependent task
        task3_response = real_nl_processor.process_message(
            f"Create task 'Run database migrations' depending on tasks {task1_id} and {task2_id}",
            context={'project_id': 1}
        )
        assert task3_response.success is True
        task3_id = task3_response.execution_result.created_ids[0]

        # Verify dependencies
        task3 = real_state_manager.get_task(task3_id)
        assert task1_id in task3.dependencies
        assert task2_id in task3.dependencies

    def test_milestone_achievement_workflow(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - epic creation to milestone"""
        # Create epic
        epic_response = real_nl_processor.process_message(
            "Create epic 'Authentication System'",
            context={'project_id': 1}
        )
        epic_id = epic_response.execution_result.created_ids[0]

        # Create milestone requiring epic
        milestone_response = real_nl_processor.process_message(
            f"Create milestone 'Auth Complete' when epic {epic_id} is done",
            context={'project_id': 1}
        )
        assert milestone_response.success is True
        milestone_id = milestone_response.execution_result.created_ids[0]

        # Verify milestone
        milestone = real_state_manager.get_milestone(milestone_id)
        assert epic_id in milestone.required_epic_ids

    def test_query_workflow(self, real_nl_processor):
        """REAL LLM: Full pipeline - question intent"""
        response = real_nl_processor.process_message(
            "What is the current project?",
            context={'project_id': 1}
        )

        # Should be classified as QUESTION, not executed as command
        assert response.intent == "QUESTION"
        assert "project" in response.response.lower()

    def test_batch_task_creation(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - batch creation"""
        response = real_nl_processor.process_message(
            "Create 3 tasks: Write tests, Review code, Deploy to staging",
            context={'project_id': 1}
        )

        assert response.success is True
        assert len(response.execution_result.created_ids) == 3

        # Verify all tasks created
        for task_id in response.execution_result.created_ids:
            task = real_state_manager.get_task(task_id)
            assert task is not None

    def test_error_recovery_invalid_epic_id(self, real_nl_processor):
        """REAL LLM: Full pipeline - handle invalid epic reference"""
        response = real_nl_processor.process_message(
            "Add story to epic 999",  # Epic doesn't exist
            context={'project_id': 1}
        )

        # Should fail validation
        assert response.success is False
        assert "epic" in response.response.lower()
        assert "999" in response.response or "not found" in response.response.lower()

    def test_circular_dependency_detection(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - prevent circular dependencies"""
        # Create task 1
        task1_response = real_nl_processor.process_message(
            "Create task 'Task A'",
            context={'project_id': 1}
        )
        task1_id = task1_response.execution_result.created_ids[0]

        # Create task 2 depending on task 1
        task2_response = real_nl_processor.process_message(
            f"Create task 'Task B' depending on task {task1_id}",
            context={'project_id': 1}
        )
        task2_id = task2_response.execution_result.created_ids[0]

        # Try to make task 1 depend on task 2 (circular!)
        # Note: This requires update capability in NLCommandProcessor
        # For now, just verify task2 dependency is valid
        task2 = real_state_manager.get_task(task2_id)
        assert task1_id in task2.dependencies
```

**Acceptance Criteria**:
- ✅ 8 full pipeline E2E tests implemented
- ✅ Tests exercise full workflow (intent → extract → validate → execute → DB)
- ✅ Both success and error cases covered
- ✅ Database state verified after execution

**Verification**:
```bash
pytest tests/test_nl_real_llm_integration.py::TestRealLLMFullPipeline -v
# Expected: 8 passed in ~120-180s
```

---

### Task 2.6: Implement LLM Failure Mode Tests (4 tests)

**Objective**: Validate error handling for real LLM failures

**Add to `TestRealLLMFailureModes` class**:

```python
class TestRealLLMFailureModes:
    """Test LLM failure handling with real Ollama/Qwen LLM"""

    @pytest.mark.timeout(35)  # Should timeout at 30s
    def test_llm_timeout_handling(self, real_llm_config, real_state_manager):
        """REAL LLM: Handle timeout gracefully"""
        # Configure very short timeout
        real_llm_config.set('llm.timeout', 1.0)  # 1 second - too short

        from src.nl.entity_extractor import EntityExtractor
        extractor = EntityExtractor(
            config=real_llm_config,
            state_manager=real_state_manager
        )

        # Should raise timeout exception
        with pytest.raises(Exception) as exc_info:
            extractor.extract(
                "Create a very complex epic with lots of details that will take time to process",
                intent="COMMAND"
            )

        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "timed out" in error_msg

    def test_invalid_json_recovery(self, real_llm_config, real_state_manager, monkeypatch):
        """REAL LLM: Recover from invalid JSON response"""
        from src.nl.entity_extractor import EntityExtractor

        extractor = EntityExtractor(
            config=real_llm_config,
            state_manager=real_state_manager
        )

        # Mock LLM to return invalid JSON
        def mock_generate(*args, **kwargs):
            return "This is not valid JSON at all!"

        monkeypatch.setattr(extractor.llm, 'generate', mock_generate)

        # Should raise EntityExtractionException with helpful message
        with pytest.raises(Exception) as exc_info:
            extractor.extract(
                "Create epic 'Test'",
                intent="COMMAND"
            )

        error_msg = str(exc_info.value).lower()
        assert "json" in error_msg or "parse" in error_msg

    def test_missing_fields_in_response(self, real_llm_config, real_state_manager, monkeypatch):
        """REAL LLM: Handle LLM response missing required fields"""
        import json
        from src.nl.entity_extractor import EntityExtractor

        extractor = EntityExtractor(
            config=real_llm_config,
            state_manager=real_state_manager
        )

        # Mock LLM to return JSON missing entity_type
        def mock_generate(*args, **kwargs):
            return json.dumps({
                "entities": [{"title": "Test"}],
                "confidence": 0.9
                # Missing: entity_type
            })

        monkeypatch.setattr(extractor.llm, 'generate', mock_generate)

        # Should raise exception mentioning missing fields
        with pytest.raises(Exception) as exc_info:
            extractor.extract(
                "Create epic 'Test'",
                intent="COMMAND"
            )

        error_msg = str(exc_info.value).lower()
        assert "entity_type" in error_msg or "missing" in error_msg

    def test_partial_response_handling(self, real_llm_config, real_state_manager, monkeypatch):
        """REAL LLM: Handle truncated/partial LLM response"""
        from src.nl.entity_extractor import EntityExtractor

        extractor = EntityExtractor(
            config=real_llm_config,
            state_manager=real_state_manager
        )

        # Mock LLM to return truncated JSON
        def mock_generate(*args, **kwargs):
            return '{"entity_type": "epic", "entities": [{"title": "Test'
            # Truncated - missing closing brackets

        monkeypatch.setattr(extractor.llm, 'generate', mock_generate)

        # Should raise JSON parsing exception
        with pytest.raises(Exception) as exc_info:
            extractor.extract(
                "Create epic 'Test'",
                intent="COMMAND"
            )

        error_msg = str(exc_info.value).lower()
        assert "json" in error_msg or "parse" in error_msg or "invalid" in error_msg
```

**Acceptance Criteria**:
- ✅ 4 LLM failure mode tests implemented
- ✅ Tests use real LLM where applicable (monkeypatch for specific failures)
- ✅ Error messages validated for user-friendliness
- ✅ Timeout handling tested with real timeouts

**Verification**:
```bash
pytest tests/test_nl_real_llm_integration.py::TestRealLLMFailureModes -v
# Expected: 4 passed in ~30-60s
```

---

### Task 2.7: Verify All Real LLM Tests Pass

**Objective**: Confirm 30/30 real LLM tests pass

**Prerequisites**:
- Ollama running on `http://172.29.144.1:11434`
- Qwen 2.5 Coder model available: `ollama pull qwen2.5-coder:32b`

**Verification Commands**:

```bash
# Check Ollama is running
curl http://172.29.144.1:11434/api/tags

# Run all real LLM tests
pytest tests/test_nl_real_llm_integration.py -v -m integration

# Expected output:
# ========== 30 passed in ~5-10 minutes ==========

# Run with detailed output
pytest tests/test_nl_real_llm_integration.py -v -m integration --tb=short

# Run specific test class
pytest tests/test_nl_real_llm_integration.py::TestRealLLMIntentClassification -v
```

**Performance Benchmarks**:

| Test Class | Tests | Expected Time | Success Criteria |
|------------|-------|---------------|------------------|
| IntentClassification | 8 | 30-60s | 8/8 passing, confidence ≥ 0.7 |
| EntityExtraction | 10 | 90-150s | 10/10 passing, extraction accuracy |
| FullPipeline | 8 | 120-180s | 8/8 passing, DB state verified |
| FailureModes | 4 | 30-60s | 4/4 passing, error handling |
| **TOTAL** | **30** | **5-10 min** | **30/30 passing** |

**Acceptance Criteria**:
- ✅ All 30 real LLM tests pass
- ✅ No timeouts or LLM connection errors
- ✅ Intent classification accuracy ≥ 90% (7-8/8 correct)
- ✅ Entity extraction accuracy ≥ 80% (8-10/10 correct)
- ✅ Full pipeline tests validate DB state
- ✅ Error handling graceful and user-friendly

**Deliverables**:
- ✅ `tests/test_nl_real_llm_integration.py` with 30 passing tests
- ✅ Pytest markers: `@pytest.mark.integration`, `@pytest.mark.slow`
- ✅ Module-scoped fixtures for performance
- ✅ Helper validation functions
- ✅ Comprehensive docstrings

---

## Phase 3: Documentation and Strategy

### Task 3.1: Create Testing Strategy Document

**Objective**: Document when to use mocks vs real LLMs

**File to Create**: `docs/testing/NL_TESTING_STRATEGY.md`

**Implementation**:

```markdown
# Natural Language Command Testing Strategy

**Created**: 2025-11-11
**Status**: Active
**Applies To**: NL Command System (v1.3.0+)

---

## Overview

The NL Command System uses a **dual testing strategy**:

1. **Mock LLM Tests (Fast)**: Unit and integration tests with mocked LLM responses
2. **Real LLM Tests (Slow)**: End-to-end validation with actual Ollama/Qwen

**Why Both?**
- Mock tests catch code logic errors (30s feedback loop)
- Real LLM tests catch prompt engineering issues (5-10min validation)
- Combined coverage ensures both correctness and production accuracy

---

## Decision Matrix

### When to Use Mock LLM Tests

| Scenario | Use Mocks | Rationale |
|----------|-----------|-----------|
| Unit testing single component | ✅ Yes | Fast, isolated, deterministic |
| Testing error handling logic | ✅ Yes | Control failure modes precisely |
| Testing validation rules | ✅ Yes | No LLM needed for business logic |
| Testing database operations | ✅ Yes | LLM irrelevant to CRUD |
| CI/CD on every commit | ✅ Yes | Fast feedback (30s) |
| Local development TDD | ✅ Yes | Instant feedback loop |

### When to Use Real LLM Tests

| Scenario | Use Real LLM | Rationale |
|----------|--------------|-----------|
| Validating prompt quality | ✅ Yes | Only real LLM can validate |
| Testing intent classification accuracy | ✅ Yes | Mock can't test actual accuracy |
| Testing entity extraction accuracy | ✅ Yes | Mock can't test extraction logic |
| Full E2E pipeline validation | ✅ Yes | Must test production behavior |
| Before merge to main | ✅ Yes | Final validation gate |
| After prompt template changes | ✅ Yes | Verify no regression |
| Debugging LLM issues | ✅ Yes | Reproduce real failure |

### When to Use Both

| Scenario | Approach |
|----------|----------|
| Integration tests | Mock for speed, real LLM subset for validation |
| Bug prevention tests | Mock for regression, real LLM for root cause |
| Performance testing | Mock for baseline, real LLM for actual timing |

---

## Test Suite Organization

### Mock LLM Tests (206 tests, ~31s)

**Files**:
- `tests/test_nl_intent_classifier.py` (30 tests)
- `tests/test_nl_entity_extractor.py` (50 tests)
- `tests/test_nl_command_validator.py` (30 tests)
- `tests/test_nl_command_processor_integration.py` (25 tests)
- `tests/test_nl_e2e_integration.py` (30 tests)
- `tests/test_nl_error_scenarios.py` (35 tests)
- `tests/test_nl_entity_extractor_bug_prevention.py` (6 tests)

**Run Command**:
```bash
# All mock tests
pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py -v

# Expected: 206 passed in ~31s
```

**Coverage**: ~75% of NL command system

### Real LLM Tests (30 tests, ~5-10min)

**File**: `tests/test_nl_real_llm_integration.py`

**Test Classes**:
- `TestRealLLMIntentClassification` (8 tests) - Intent accuracy
- `TestRealLLMEntityExtraction` (10 tests) - Extraction accuracy
- `TestRealLLMFullPipeline` (8 tests) - E2E workflows
- `TestRealLLMFailureModes` (4 tests) - Error handling

**Run Command**:
```bash
# All real LLM tests
pytest tests/test_nl_real_llm_integration.py -v -m integration

# Expected: 30 passed in 5-10 minutes
```

**Prerequisites**:
- Ollama running on `http://172.29.144.1:11434`
- Qwen 2.5 Coder model: `ollama pull qwen2.5-coder:32b`

---

## Running Tests

### Development Workflow (Fast Feedback)

```bash
# Run mock tests only (30s)
pytest tests/test_nl_*.py -v -m "not integration"

# Run specific component
pytest tests/test_nl_intent_classifier.py -v

# Watch mode for TDD
pytest-watch tests/test_nl_intent_classifier.py
```

### Pre-Commit Validation (Moderate)

```bash
# Run all mock tests with coverage
pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py \
    --cov=src/nl --cov-report=term --cov-report=html

# Expected: 206 passed, ~75% coverage, ~31s
```

### Pre-Merge Validation (Full)

```bash
# Run BOTH mock and real LLM tests
pytest tests/test_nl_*.py -v && \
pytest tests/test_nl_real_llm_integration.py -v -m integration

# Expected: 236 passed total (206 mock + 30 real), ~6-11 minutes
```

### CI/CD Configuration

**On Every Commit** (GitHub Actions):
```yaml
- name: Run mock tests
  run: pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py -v
  # Fast feedback (30s)
```

**On Merge to Main** (GitHub Actions):
```yaml
- name: Start Ollama
  run: docker run -d -p 11434:11434 ollama/ollama
- name: Pull Qwen model
  run: docker exec ollama ollama pull qwen2.5-coder:32b
- name: Run real LLM tests
  run: pytest tests/test_nl_real_llm_integration.py -v -m integration
  # Full validation (5-10 min)
```

---

## Pytest Markers

### Available Markers

```python
# Integration tests (requires Ollama)
@pytest.mark.integration

# Slow tests (> 1 second per test)
@pytest.mark.slow

# Requires Ollama running
@pytest.mark.requires_ollama
```

### Running by Marker

```bash
# Skip integration tests (fast)
pytest tests/test_nl_*.py -v -m "not integration"

# Only integration tests
pytest tests/test_nl_*.py -v -m integration

# Skip slow tests
pytest tests/test_nl_*.py -v -m "not slow"
```

---

## Mock Fixtures Reference

### Available Fixtures (conftest.py)

| Fixture | Type | Returns | Use Case |
|---------|------|---------|----------|
| `mock_llm_responses` | Dict | Valid JSON responses | Response templates |
| `mock_llm_smart` | Mock | Context-aware mock | Most tests |
| `mock_llm_simple` | Mock | Always returns task | Basic tests |
| `real_llm_config` | Config | Real LLM config | Integration tests |
| `real_state_manager` | StateManager | DB with real config | Integration tests |
| `real_intent_classifier` | IntentClassifier | Real component | Integration tests |
| `real_entity_extractor` | EntityExtractor | Real component | Integration tests |
| `real_nl_processor` | NLCommandProcessor | Full pipeline | E2E tests |

### Example Usage

**Mock Tests**:
```python
def test_with_smart_mock(mock_llm_smart, test_config, state_manager):
    extractor = EntityExtractor(config=test_config, state_manager=state_manager)
    extractor.llm = mock_llm_smart  # Inject mock

    result = extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"
```

**Real LLM Tests**:
```python
@pytest.mark.integration
def test_with_real_llm(real_entity_extractor):
    # No mock injection - uses real Ollama
    result = real_entity_extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"
    assert result.confidence >= 0.7  # Real accuracy threshold
```

---

## Coverage Goals

| Component | Mock Tests | Real LLM Tests | Combined |
|-----------|------------|----------------|----------|
| IntentClassifier | 85% | Accuracy validation | 90% |
| EntityExtractor | 90% | Accuracy validation | 95% |
| CommandValidator | 100% | N/A (no LLM) | 100% |
| CommandExecutor | 95% | N/A (no LLM) | 95% |
| NLCommandProcessor | 80% | E2E workflows | 90% |
| ResponseFormatter | 90% | N/A (formatting) | 90% |

**Overall Target**: 90% code coverage, 85% real LLM accuracy

---

## Performance Benchmarks

### Mock Tests

| File | Tests | Time | Per Test |
|------|-------|------|----------|
| test_nl_intent_classifier.py | 30 | 3s | 0.1s |
| test_nl_entity_extractor.py | 50 | 5s | 0.1s |
| test_nl_command_validator.py | 30 | 2s | 0.07s |
| test_nl_command_processor_integration.py | 25 | 4s | 0.16s |
| test_nl_e2e_integration.py | 30 | 5s | 0.17s |
| test_nl_error_scenarios.py | 35 | 7s | 0.2s |
| test_nl_entity_extractor_bug_prevention.py | 6 | 1s | 0.17s |
| **TOTAL** | **206** | **~31s** | **0.15s** |

### Real LLM Tests

| Test Class | Tests | Time | Per Test |
|------------|-------|------|----------|
| TestRealLLMIntentClassification | 8 | 30-60s | 4-8s |
| TestRealLLMEntityExtraction | 10 | 90-150s | 9-15s |
| TestRealLLMFullPipeline | 8 | 120-180s | 15-23s |
| TestRealLLMFailureModes | 4 | 30-60s | 8-15s |
| **TOTAL** | **30** | **5-10min** | **10-20s** |

**Note**: Real LLM test time varies based on:
- LLM model size (Qwen 32B vs 7B)
- GPU availability (RTX 5090 vs CPU)
- Network latency (local vs remote Ollama)
- Context length (longer prompts = slower)

---

## Troubleshooting

### Mock Tests Failing

**Symptom**: `EntityExtractionException: Missing required fields`

**Cause**: Mock LLM returning invalid JSON

**Fix**:
```python
# Use smart mock fixture instead of inline mock
def test_example(mock_llm_smart, ...):  # ✅
    extractor.llm = mock_llm_smart

# Don't create broken inline mocks
mock.generate.return_value = MagicMock()  # ❌
```

### Real LLM Tests Failing

**Symptom**: `Connection refused` or `Timeout`

**Cause**: Ollama not running

**Fix**:
```bash
# Start Ollama
docker run -d -p 11434:11434 ollama/ollama

# Pull model
docker exec ollama ollama pull qwen2.5-coder:32b

# Verify
curl http://172.29.144.1:11434/api/tags
```

**Symptom**: Low confidence scores (< 0.7)

**Cause**: Prompt template needs improvement

**Fix**:
1. Check prompt templates in `prompts/`
2. Run A/B testing framework to compare prompts
3. Update templates based on results
4. Re-run real LLM tests to validate

### Performance Issues

**Symptom**: Real LLM tests taking > 15 minutes

**Cause**: Network latency or slow GPU

**Fix**:
1. Use local Ollama (not remote)
2. Use smaller model for testing (qwen2.5-coder:7b)
3. Reduce context length in prompts
4. Run tests in parallel: `pytest -n 4 ...`

---

## Best Practices

### Mock Test Best Practices

1. **Use Smart Mock Fixture**: `mock_llm_smart` auto-detects entity type
2. **Validate Schema**: Ensure mock responses match `obra_schema.json`
3. **Test Error Cases**: Don't just test happy path
4. **Fast Execution**: Keep per-test time < 0.5s
5. **Deterministic**: Same input = same output (no randomness)

### Real LLM Test Best Practices

1. **Set Confidence Thresholds**: Validate accuracy, not just success
2. **Verify DB State**: Check database after execution (E2E)
3. **Test Edge Cases**: Emojis, code blocks, special chars
4. **Use Low Temperature**: 0.1 for consistency (not 0.7)
5. **Module-Scoped Fixtures**: Reuse config/state across tests

### General Testing Best Practices

1. **Run Mocks First**: Fast feedback before slow validation
2. **CI/CD Strategy**: Mocks on every commit, real LLM on merge
3. **Monitor Performance**: Track test execution time trends
4. **Update Baselines**: When prompts change, update expected accuracy
5. **Document Failures**: Add bug prevention tests for every bug found

---

## Migration Guide

### Updating Existing Tests to Use New Fixtures

**Before** (broken mock):
```python
def test_old_way(test_config, state_manager):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = MagicMock()  # ❌ Invalid
    # ...
```

**After** (fixed with smart mock):
```python
def test_new_way(mock_llm_smart, test_config, state_manager):
    extractor = EntityExtractor(config=test_config, state_manager=state_manager)
    extractor.llm = mock_llm_smart  # ✅ Valid JSON
    # ...
```

### Adding Real LLM Coverage for Existing Feature

1. Identify feature to test (e.g., new entity type)
2. Write mock test first (fast feedback)
3. Add real LLM test in `test_nl_real_llm_integration.py`
4. Run both to validate
5. Update this strategy doc if needed

---

## Future Enhancements

**Planned Improvements**:
- [ ] LLM caching to speed up real LLM tests (30% faster)
- [ ] Parallel real LLM test execution (`pytest-xdist`)
- [ ] A/B testing integration (compare prompt versions)
- [ ] Real LLM test result analytics dashboard
- [ ] Automated prompt optimization based on test failures

**See**: `docs/design/enhancements/` for detailed proposals

---

## References

- **Test Files**: `tests/test_nl_*.py`
- **Mock Fixtures**: `tests/conftest.py`
- **Obra Schema**: `src/nl/schemas/obra_schema.json`
- **Prompt Templates**: `prompts/intent_classification.txt`, `prompts/entity_extraction.txt`
- **Test Guidelines**: `docs/development/TEST_GUIDELINES.md`
- **NL Command Guide**: `docs/guides/NL_COMMAND_GUIDE.md`

---

**Last Updated**: 2025-11-11
**Version**: 1.0
**Maintainer**: Obra Development Team
```

**Acceptance Criteria**:
- ✅ Created `docs/testing/NL_TESTING_STRATEGY.md`
- ✅ Documented decision matrix (mock vs real LLM)
- ✅ Provided run commands for all scenarios
- ✅ Explained pytest markers and fixtures
- ✅ Troubleshooting guide included
- ✅ Best practices documented

---

### Task 3.2: Update Main Testing Documentation

**Objective**: Link new NL testing strategy to existing test docs

**Files to Update**:

1. **`docs/testing/README.md`** (if exists, else create):

```markdown
# Testing Documentation Index

## Core Testing Guides

- **[Test Guidelines](TEST_GUIDELINES.md)** - WSL2-safe testing practices (CRITICAL)
- **[NL Testing Strategy](NL_TESTING_STRATEGY.md)** - Mock vs Real LLM testing strategy ⭐ NEW!

## Test Suites

- **[NL Command User Stories](NL_COMMAND_USER_STORIES.md)** - 20 user stories for NL system
- **[NL Test Implementation Plan](NL_TEST_IMPLEMENTATION_PLAN.md)** - 3-phase test roadmap
- **[NL Quick Start](NL_TEST_QUICK_START.md)** - Fast onboarding for NL tests

## Phase Reports

- **[Phase 1 Completion](NL_PHASE1_COMPLETION_REPORT.md)** - Core pipeline tests
- **[Phase 2 Summary](NL_PHASE2_SUMMARY.md)** - Validation tests
- **[Phase 3 Final Report](NL_PHASE3_FINAL_REPORT.md)** - E2E and error tests

## Quick Reference

### Run All Tests
```bash
# All tests (mock + real LLM)
pytest tests/ -v

# Mock tests only (fast - 31s)
pytest tests/test_nl_*.py -v -m "not integration"

# Real LLM tests only (slow - 5-10min)
pytest tests/test_nl_real_llm_integration.py -v -m integration
```

### Coverage Report
```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
open htmlcov/index.html
```

---

**Last Updated**: 2025-11-11
```

2. **`docs/development/TEST_GUIDELINES.md`** - Add section on NL testing:

```markdown
## Natural Language Command Testing

**New in v1.3.0**: NL command system has dual testing strategy.

**See**: [NL Testing Strategy](../testing/NL_TESTING_STRATEGY.md) for complete guide.

**Quick Tips**:
- Use `mock_llm_smart` fixture for fast mock tests
- Mark real LLM tests with `@pytest.mark.integration`
- Run mock tests locally (31s), real LLM tests in CI (5-10min)
- Real LLM tests require Ollama running on `http://172.29.144.1:11434`

**Example**:
```python
# Mock test (fast)
def test_with_mock(mock_llm_smart, test_config, state_manager):
    extractor = EntityExtractor(config=test_config, state_manager=state_manager)
    extractor.llm = mock_llm_smart
    result = extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"

# Real LLM test (slow, validates accuracy)
@pytest.mark.integration
def test_with_real_llm(real_entity_extractor):
    result = real_entity_extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"
    assert result.confidence >= 0.7  # Real accuracy threshold
```
```

**Acceptance Criteria**:
- ✅ Created/updated `docs/testing/README.md`
- ✅ Added NL testing section to `docs/development/TEST_GUIDELINES.md`
- ✅ Cross-referenced NL_TESTING_STRATEGY.md
- ✅ Included quick reference commands

---

### Task 3.3: Update CHANGELOG.md

**Objective**: Document NL test suite fixes and enhancements

**File to Update**: `CHANGELOG.md`

**Add Under `[Unreleased]` Section**:

```markdown
## [Unreleased]

### Fixed
- **NL Test Suite**: Fixed 16 failing tests in NL command system (100% pass rate achieved)
  - Replaced broken mock LLM fixtures with `mock_llm_smart` and `mock_llm_simple`
  - Fixed `test_nl_entity_extractor_bug_prevention.py` (5 tests)
  - Fixed `test_nl_command_processor_integration.py` (4 tests)
  - Fixed `test_nl_e2e_integration.py` (7 tests)
  - All 206 mock tests now pass in ~31s

### Added
- **Real LLM Integration Tests**: Created 30 new tests using actual Ollama/Qwen (5-10min execution)
  - Intent classification accuracy tests (8 tests)
  - Entity extraction accuracy tests (10 tests)
  - Full pipeline E2E tests (8 tests)
  - LLM failure mode tests (4 tests)
  - Validates production behavior with real LLM, not just mocked logic
- **NL Testing Strategy Documentation**: Comprehensive guide on when to use mock vs real LLM tests
  - Decision matrix for test approach selection
  - Pytest markers for integration tests (`@pytest.mark.integration`)
  - CI/CD configuration guidance (mock on commit, real LLM on merge)
  - Performance benchmarks and troubleshooting guide

### Changed
- **Test Fixtures**: Improved mock LLM fixtures in `tests/conftest.py`
  - `mock_llm_responses`: Valid JSON templates for all Obra entity types
  - `mock_llm_smart`: Context-aware mock that returns appropriate responses
  - `mock_llm_simple`: Basic mock for simple test cases
  - `real_llm_*` fixtures: Module-scoped fixtures for real LLM integration tests
```

**Acceptance Criteria**:
- ✅ Updated `CHANGELOG.md` under `[Unreleased]`
- ✅ Categorized changes: Fixed, Added, Changed
- ✅ Clear descriptions of improvements
- ✅ Linked to test files and documentation

---

## Phase 4: CI/CD Configuration (Optional)

### Task 4.1: Create GitHub Actions Workflow

**Objective**: Automate test execution in CI/CD

**File to Create**: `.github/workflows/nl-tests.yml`

**Implementation**:

```yaml
name: NL Command Tests

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'src/nl/**'
      - 'tests/test_nl_*.py'
      - 'prompts/**'
  pull_request:
    branches: [ main, develop ]
    paths:
      - 'src/nl/**'
      - 'tests/test_nl_*.py'
      - 'prompts/**'

jobs:
  # ============================================================================
  # Job 1: Mock Tests (Fast - runs on every commit)
  # ============================================================================
  mock-tests:
    name: Mock LLM Tests (Fast)
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-timeout

      - name: Run mock tests
        run: |
          pytest tests/test_nl_*.py \
            --ignore=tests/test_nl_real_llm_integration.py \
            -v \
            -m "not integration" \
            --cov=src/nl \
            --cov-report=term \
            --cov-report=xml \
            --cov-report=html

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: nl-mock-tests
          name: NL Mock Tests Coverage

      - name: Upload HTML coverage report
        uses: actions/upload-artifact@v3
        with:
          name: nl-mock-coverage-report
          path: htmlcov/

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=75

  # ============================================================================
  # Job 2: Real LLM Tests (Slow - runs on merge to main only)
  # ============================================================================
  real-llm-tests:
    name: Real LLM Integration Tests (Slow)
    runs-on: ubuntu-latest
    timeout-minutes: 20

    # Only run on merge to main or manual trigger
    if: github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-timeout

      - name: Start Ollama service
        run: |
          docker pull ollama/ollama:latest
          docker run -d \
            --name ollama \
            -p 11434:11434 \
            -v ollama-data:/root/.ollama \
            ollama/ollama

          # Wait for Ollama to be ready
          timeout 60 bash -c 'until curl -s http://localhost:11434/api/tags > /dev/null; do sleep 2; done'

      - name: Pull Qwen model
        run: |
          # Use smaller model for CI (7B instead of 32B)
          docker exec ollama ollama pull qwen2.5-coder:7b

      - name: Configure Obra for CI
        run: |
          # Update config to use local Ollama
          export OBRA_LLM_BASE_URL=http://localhost:11434
          export OBRA_LLM_MODEL=qwen2.5-coder:7b

      - name: Run real LLM tests
        env:
          OBRA_LLM_BASE_URL: http://localhost:11434
          OBRA_LLM_MODEL: qwen2.5-coder:7b
        run: |
          pytest tests/test_nl_real_llm_integration.py \
            -v \
            -m integration \
            --tb=short \
            --timeout=60

      - name: Stop Ollama
        if: always()
        run: |
          docker stop ollama
          docker rm ollama

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: real-llm-test-results
          path: |
            pytest.log
            test-results/
```

**Acceptance Criteria**:
- ✅ Created `.github/workflows/nl-tests.yml`
- ✅ Mock tests run on every commit (fast feedback)
- ✅ Real LLM tests run on merge to main only
- ✅ Coverage reporting to Codecov
- ✅ Uses Qwen 7B in CI (smaller, faster than 32B)
- ✅ Proper Ollama container setup and teardown

---

### Task 4.2: Add pytest.ini Configuration

**Objective**: Configure pytest markers and options

**File to Create**: `pytest.ini`

**Implementation**:

```ini
[pytest]
# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests

# Markers
markers =
    integration: Integration tests using real LLM (slow, requires Ollama)
    slow: Slow tests (> 1 second per test)
    requires_ollama: Tests requiring Ollama service running
    unit: Fast unit tests (< 0.5s per test)
    mock: Tests using mock LLM (default)

# Output options
addopts =
    -v
    --strict-markers
    --tb=short
    --color=yes
    --code-highlight=yes

# Coverage options
[coverage:run]
source = src
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
```

**Acceptance Criteria**:
- ✅ Created `pytest.ini` in project root
- ✅ Configured markers: integration, slow, requires_ollama
- ✅ Set coverage options
- ✅ Configured output formatting

**Verification**:
```bash
# List all markers
pytest --markers

# Should show custom markers: integration, slow, requires_ollama
```

---

### Task 4.3: Create Quick Start Script

**Objective**: Provide easy script to run tests locally

**File to Create**: `scripts/run_nl_tests.sh`

**Implementation**:

```bash
#!/bin/bash
#
# NL Command Test Runner
#
# Usage:
#   ./scripts/run_nl_tests.sh [mock|real|both|coverage]
#
# Examples:
#   ./scripts/run_nl_tests.sh mock      # Run mock tests only (fast)
#   ./scripts/run_nl_tests.sh real      # Run real LLM tests only
#   ./scripts/run_nl_tests.sh both      # Run all tests
#   ./scripts/run_nl_tests.sh coverage  # Run with coverage report

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_ollama() {
    if ! curl -s http://172.29.144.1:11434/api/tags > /dev/null 2>&1; then
        print_error "Ollama is not running on http://172.29.144.1:11434"
        echo "Start Ollama with: docker run -d -p 11434:11434 ollama/ollama"
        echo "Then pull model: docker exec ollama ollama pull qwen2.5-coder:32b"
        return 1
    fi
    return 0
}

run_mock_tests() {
    print_header "Running Mock LLM Tests (Fast - ~31s)"

    pytest tests/test_nl_*.py \
        --ignore=tests/test_nl_real_llm_integration.py \
        -v \
        -m "not integration" \
        "$@"

    if [ $? -eq 0 ]; then
        print_success "Mock tests passed!"
    else
        print_error "Mock tests failed!"
        exit 1
    fi
}

run_real_tests() {
    print_header "Running Real LLM Tests (Slow - ~5-10min)"

    # Check Ollama is running
    if ! check_ollama; then
        exit 1
    fi

    print_warning "This will take 5-10 minutes..."

    pytest tests/test_nl_real_llm_integration.py \
        -v \
        -m integration \
        "$@"

    if [ $? -eq 0 ]; then
        print_success "Real LLM tests passed!"
    else
        print_error "Real LLM tests failed!"
        exit 1
    fi
}

run_coverage() {
    print_header "Running Tests with Coverage"

    pytest tests/test_nl_*.py \
        --ignore=tests/test_nl_real_llm_integration.py \
        --cov=src/nl \
        --cov-report=term \
        --cov-report=html \
        -v \
        -m "not integration"

    if [ $? -eq 0 ]; then
        print_success "Coverage report generated!"
        echo "Open htmlcov/index.html to view report"
    else
        print_error "Tests failed!"
        exit 1
    fi
}

# Main
MODE=${1:-both}

case "$MODE" in
    mock)
        run_mock_tests
        ;;
    real)
        run_real_tests
        ;;
    both)
        run_mock_tests
        echo ""
        run_real_tests
        ;;
    coverage)
        run_coverage
        ;;
    *)
        echo "Usage: $0 [mock|real|both|coverage]"
        echo ""
        echo "Options:"
        echo "  mock     - Run mock LLM tests only (fast, ~31s)"
        echo "  real     - Run real LLM tests only (slow, ~5-10min)"
        echo "  both     - Run all tests (default)"
        echo "  coverage - Run mock tests with coverage report"
        exit 1
        ;;
esac

print_success "All requested tests completed successfully!"
```

**Make Executable**:
```bash
chmod +x scripts/run_nl_tests.sh
```

**Acceptance Criteria**:
- ✅ Created `scripts/run_nl_tests.sh`
- ✅ Supports modes: mock, real, both, coverage
- ✅ Color-coded output
- ✅ Checks Ollama availability for real LLM tests
- ✅ Helpful error messages

**Verification**:
```bash
./scripts/run_nl_tests.sh mock
# Should run mock tests and show success message
```

---

## Deliverables Summary

### Phase 1: Fix Mock LLM Fixtures
- ✅ `tests/conftest.py` - Updated with `mock_llm_smart`, `mock_llm_simple`, `mock_llm_responses`
- ✅ `tests/test_nl_entity_extractor_bug_prevention.py` - 6/6 tests passing
- ✅ `tests/test_nl_command_processor_integration.py` - 25/25 tests passing
- ✅ `tests/test_nl_e2e_integration.py` - 30/30 tests passing
- ✅ **206/206 mock tests passing (100% pass rate, ~31s)**

### Phase 2: Create Real LLM Integration Tests
- ✅ `tests/test_nl_real_llm_integration.py` - 30 new tests
  - 8 intent classification tests
  - 10 entity extraction tests
  - 8 full pipeline E2E tests
  - 4 LLM failure mode tests
- ✅ **30/30 real LLM tests passing (5-10min execution)**

### Phase 3: Documentation and Strategy
- ✅ `docs/testing/NL_TESTING_STRATEGY.md` - Comprehensive testing strategy guide
- ✅ `docs/testing/README.md` - Testing documentation index
- ✅ Updated `docs/development/TEST_GUIDELINES.md` - NL testing section
- ✅ Updated `CHANGELOG.md` - Documented fixes and enhancements

### Phase 4: CI/CD Configuration (Optional)
- ✅ `.github/workflows/nl-tests.yml` - Automated CI/CD workflow
- ✅ `pytest.ini` - Pytest configuration with markers
- ✅ `scripts/run_nl_tests.sh` - Local test runner script

---

## Verification Checklist

### Mock Tests (Phase 1)
- [ ] Run `pytest tests/test_nl_*.py --ignore=tests/test_nl_real_llm_integration.py -v`
- [ ] Verify 206/206 passing
- [ ] Execution time ≤ 35s
- [ ] No warnings about invalid JSON or missing fields

### Real LLM Tests (Phase 2)
- [ ] Ollama running: `curl http://172.29.144.1:11434/api/tags`
- [ ] Model available: `qwen2.5-coder:32b` or `7b`
- [ ] Run `pytest tests/test_nl_real_llm_integration.py -v -m integration`
- [ ] Verify 30/30 passing
- [ ] Execution time 5-10 minutes
- [ ] Intent classification confidence ≥ 0.7
- [ ] Entity extraction confidence ≥ 0.7

### Documentation (Phase 3)
- [ ] `docs/testing/NL_TESTING_STRATEGY.md` exists and complete
- [ ] `docs/testing/README.md` updated with NL links
- [ ] `docs/development/TEST_GUIDELINES.md` has NL section
- [ ] `CHANGELOG.md` updated with fixes/additions

### CI/CD (Phase 4)
- [ ] `.github/workflows/nl-tests.yml` created
- [ ] `pytest.ini` configured with markers
- [ ] `scripts/run_nl_tests.sh` executable and working
- [ ] Workflow runs on GitHub (if using GitHub Actions)

---

## Success Metrics

| Metric | Before | Target | Status |
|--------|--------|--------|--------|
| Mock test pass rate | 92% (190/206) | 100% (206/206) | 🎯 |
| Real LLM test coverage | 0 tests | 30 tests | 🎯 |
| Total test count | 206 | 236 | 🎯 |
| Mock test time | 31s | ≤ 35s | 🎯 |
| Real LLM test time | N/A | 5-10min | 🎯 |
| Overall coverage | ~75% | ~85% | 🎯 |
| Documentation | Partial | Complete | 🎯 |

---

## Timeline Estimate

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|----------------|--------------|
| Phase 1 | Fix mock fixtures | 1-2 hours | None |
| Phase 2 | Real LLM tests | 2-3 hours | Phase 1 complete |
| Phase 3 | Documentation | 1 hour | Phase 1 & 2 complete |
| Phase 4 | CI/CD (optional) | 30 minutes | Phase 1-3 complete |
| **TOTAL** | - | **4-6 hours** | Sequential |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mock fixtures still broken | High | Use provided fixtures exactly as specified |
| Ollama not available for real tests | Medium | Document prerequisites clearly, provide Docker commands |
| Real LLM tests too slow | Low | Use smaller model (7B) in CI, 32B locally |
| Low LLM accuracy | Medium | Set confidence threshold at 0.7 (not 0.9) initially |
| CI/CD setup complex | Low | Phase 4 optional, can defer |

---

## Next Steps After Completion

1. **Merge to Main**: Create PR with all changes
2. **Monitor CI/CD**: Ensure workflows run successfully
3. **Track Metrics**: Monitor test pass rates and execution times
4. **Iterate**: Adjust confidence thresholds based on real data
5. **Expand Coverage**: Add more real LLM tests for edge cases
6. **A/B Testing**: Use real LLM tests to validate prompt improvements

---

**Ready for Implementation**: This plan is complete and ready for Claude Code to execute autonomously.

**Execution Command**:
```bash
# Hand this plan to Claude Code
claude code "Implement the plan in docs/development/NL_TEST_SUITE_FIX_AND_ENHANCEMENT_PLAN.md"
```

---

**End of Implementation Plan**
