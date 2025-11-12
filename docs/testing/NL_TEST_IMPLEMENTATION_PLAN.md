# NL Command System - Test Implementation Plan

**Goal:** Achieve ≥85% coverage for all `src/nl/*.py` modules to catch bugs like the `entity_type=None` error before manual testing.

**Current Coverage:** 0% (no tests exist)

**Estimated Effort:** 12-15 hours total (300-430 test cases)

---

## Test File Structure

```
tests/
├── test_nl_intent_classifier.py      # US-NL-001, 004, 008, 011, 015, 016
├── test_nl_entity_extractor.py       # US-NL-001, 006, 007, 008, 016, 019
├── test_nl_command_validator.py      # US-NL-008, 009, 010, 017
├── test_nl_command_executor.py       # US-NL-002, 003, 005, 009, 010, 014
├── test_nl_response_formatter.py     # US-NL-002, 003, 004, 005
├── test_nl_command_processor.py      # All 20 stories (integration)
├── test_nl_integration_e2e.py        # End-to-end workflows
└── test_nl_error_scenarios.py        # US-NL-015, 016, 017, 018, 019
```

---

## Phase 1: Core Pipeline (Priority 1) - 4 hours

**Goal:** Catch the critical bugs (entity extraction, intent classification)

### File 1: `tests/test_nl_intent_classifier.py`
**Coverage Target:** 85% of `src/nl/intent_classifier.py`

**Test Cases (30 total):**
```python
class TestIntentClassification:
    # Basic classification (10 cases)
    def test_classify_command_create()           # "Create epic"
    def test_classify_command_update()           # "Update task"
    def test_classify_command_query()            # "What is..."
    def test_classify_question_forward()         # "Send to Claude:"
    def test_classify_clarification_needed()     # "status" (ambiguous)

    # Confidence scoring (10 cases)
    def test_high_confidence_command()           # Clear intent
    def test_medium_confidence_question()        # Somewhat clear
    def test_low_confidence_ambiguous()          # Very unclear

    # Edge cases (10 cases)
    def test_empty_input()
    def test_very_long_input()                   # 1000+ chars
    def test_special_characters()
    def test_non_english_input()                 # UTF-8
    def test_llm_timeout()                       # Mock timeout
    def test_llm_malformed_response()            # Invalid JSON
```

**US Coverage:** US-NL-001, US-NL-004, US-NL-008, US-NL-011, US-NL-015, US-NL-018

---

### File 2: `tests/test_nl_entity_extractor.py`
**Coverage Target:** 90% of `src/nl/entity_extractor.py` (CRITICAL - this is where the bug was)

**Test Cases (50 total):**
```python
class TestEntityExtraction:
    # Valid entity types (10 cases)
    def test_extract_project_entity()
    def test_extract_epic_entity()
    def test_extract_story_entity()
    def test_extract_task_entity()
    def test_extract_subtask_entity()
    def test_extract_milestone_entity()

    # Bug prevention (US-NL-016) - 15 cases
    def test_entity_type_none()                  # THE BUG CASE! ⭐
    def test_entity_type_missing()               # Field not in response
    def test_entity_type_invalid_string()        # "feature" not valid
    def test_entity_type_wrong_type()            # Integer instead of string
    def test_entities_field_missing()
    def test_entities_not_a_list()
    def test_malformed_json_response()
    def test_incomplete_entity_data()

    # ID extraction (10 cases)
    def test_extract_single_id()                 # "task 42"
    def test_extract_multiple_ids()              # "tasks 1, 2, 3"
    def test_extract_id_from_context()           # "mark it completed" (it=previous ID)

    # Name extraction (10 cases)
    def test_extract_exact_name()                # "auth epic"
    def test_extract_fuzzy_name()                # "authentification" → "authentication"
    def test_extract_partial_name()              # "login" matches "OAuth login story"

    # Field extraction (5 cases)
    def test_extract_status_field()
    def test_extract_title_field()
    def test_extract_description_field()
```

**US Coverage:** US-NL-001, US-NL-006, US-NL-007, US-NL-008, **US-NL-016**, US-NL-019

**Critical Tests:**
```python
def test_entity_type_none(self, mock_llm, mock_state):
    """Prevent regression of the entity_type=None bug.

    Bug Reference: 2025-11-11 15:42:07 - ValueError: Invalid entity_type: None

    Expected Behavior: Should return EntityExtractionException with helpful message,
    NOT raise ValueError with Python traceback.
    """
    # Setup: Mock LLM returns entity_type=None
    mock_llm.send_prompt.return_value = json.dumps({
        "entity_type": None,  # ← The bug condition
        "entities": []
    })

    extractor = EntityExtractor(mock_llm, mock_state, config)

    # Execute and Assert
    with pytest.raises(EntityExtractionException) as exc_info:
        extractor.extract("What is the current project?", intent="COMMAND")

    # Verify error message is user-friendly
    error_msg = str(exc_info.value)
    assert "couldn't determine" in error_msg.lower()
    assert "project, epic, story, task" in error_msg.lower()
    assert "ValueError" not in error_msg  # No Python exception leakage
    assert "Traceback" not in error_msg
```

---

### File 3: `tests/test_nl_command_processor.py`
**Coverage Target:** 80% of `src/nl/nl_command_processor.py` (integration tests)

**Test Cases (40 total):**
```python
class TestProjectQueries:
    # US-NL-001: Query current project
    def test_query_current_project_success()
    def test_query_current_project_no_active()
    def test_query_current_project_entity_type_none()  # Bug case
    def test_query_variations()                        # Different phrasings

class TestWorkItemQueries:
    # US-NL-004: Query epic/story/task
    def test_query_current_epic()
    def test_query_current_story()
    def test_query_current_task()
    def test_query_no_active_work_item()

    # US-NL-006: Query by ID
    def test_query_by_id_success()
    def test_query_by_id_not_found()

class TestWorkItemCreation:
    # US-NL-008: Create work items
    def test_create_epic_success()
    def test_create_story_with_epic_id()
    def test_create_task_with_story_id()
    def test_create_missing_required_fields()

class TestMessageForwarding:
    # US-NL-011: Forward to Claude
    def test_forward_to_implementor()
    def test_forward_with_context()
    def test_forward_timeout_retry()

class TestErrorHandling:
    # US-NL-015, 016, 017
    def test_ambiguous_query_clarification()
    def test_invalid_entity_type_graceful()
    def test_missing_context_helpful_error()
```

**US Coverage:** All 20 stories (integration level)

---

## Phase 2: Advanced Features (Priority 2) - 5 hours

### File 4: `tests/test_nl_command_validator.py`
**Coverage Target:** 85% of `src/nl/command_validator.py`

**Test Cases (30 total):**
```python
class TestCommandValidation:
    # Business rule validation
    def test_validate_create_epic_rules()
    def test_validate_update_task_status_transition()
    def test_validate_dependency_no_cycles()
    def test_validate_required_fields()

    # Permission checks
    def test_validate_user_can_modify_task()
    def test_validate_readonly_fields()

    # Data type validation
    def test_validate_field_types()
    def test_validate_enum_values()
    def test_validate_date_formats()
```

**US Coverage:** US-NL-008, US-NL-009, US-NL-010, US-NL-017

---

### File 5: `tests/test_nl_command_executor.py`
**Coverage Target:** 85% of `src/nl/command_executor.py`

**Test Cases (50 total):**
```python
class TestCommandExecution:
    # Query execution (US-NL-002, 003)
    def test_execute_project_stats_query()
    def test_execute_recent_activity_query()
    def test_execute_hierarchy_query()

    # CRUD execution (US-NL-008, 009, 010)
    def test_execute_create_epic()
    def test_execute_update_task()
    def test_execute_delete_subtask()
    def test_execute_add_dependency()

    # Orchestration commands (US-NL-014)
    def test_execute_pause_orchestration()
    def test_execute_resume_orchestration()
    def test_execute_override_decision()

    # Transaction handling
    def test_execute_rollback_on_error()
    def test_execute_atomic_multi_step()
```

**US Coverage:** US-NL-002, US-NL-003, US-NL-005, US-NL-009, US-NL-010, US-NL-014

---

### File 6: `tests/test_nl_response_formatter.py`
**Coverage Target:** 80% of `src/nl/response_formatter.py`

**Test Cases (25 total):**
```python
class TestResponseFormatting:
    # Color coding
    def test_format_success_message_green()
    def test_format_error_message_red()
    def test_format_warning_message_yellow()

    # Table formatting (US-NL-002, 005)
    def test_format_project_stats_table()
    def test_format_hierarchy_tree()
    def test_format_task_list()

    # Markdown support
    def test_format_with_code_blocks()
    def test_format_with_links()
    def test_format_with_lists()
```

**US Coverage:** US-NL-002, US-NL-003, US-NL-004, US-NL-005

---

## Phase 3: Edge Cases & E2E (Priority 3) - 4 hours

### File 7: `tests/test_nl_integration_e2e.py`
**Coverage Target:** End-to-end workflows (all modules integrated)

**Test Cases (30 total):**
```python
class TestEndToEndWorkflows:
    # Complete workflows
    def test_create_epic_then_add_stories()
    def test_update_task_status_then_check_milestone()
    def test_query_hierarchy_then_modify_dependency()

    # Multi-turn conversations (US-NL-020)
    def test_conversation_with_context()
    def test_conversation_pronoun_resolution()
    def test_conversation_implicit_reference()

    # Hybrid communication (US-NL-011, 012)
    def test_optimize_prompt_then_forward_to_claude()
    def test_direct_message_to_implementor()
```

**US Coverage:** US-NL-012, US-NL-020, plus end-to-end validation of all other stories

---

### File 8: `tests/test_nl_error_scenarios.py`
**Coverage Target:** Error handling across all modules

**Test Cases (35 total):**
```python
class TestErrorScenarios:
    # LLM failures (US-NL-018)
    def test_llm_timeout_with_retry()
    def test_llm_rate_limit_backoff()
    def test_llm_malformed_json()
    def test_llm_empty_response()

    # Data validation failures
    def test_invalid_entity_id()
    def test_circular_dependency_detection()
    def test_missing_required_context()

    # Special characters (US-NL-019)
    def test_sql_injection_prevention()
    def test_xss_prevention()
    def test_unicode_handling()
    def test_emoji_handling()
    def test_code_block_handling()

    # Ambiguity handling (US-NL-015)
    def test_ambiguous_query_clarification()
    def test_multiple_match_disambiguation()
```

**US Coverage:** US-NL-015, US-NL-018, US-NL-019

---

## Quick Start: Implement Phase 1 First

### Step 1: Create Test Fixtures (30 minutes)

Add to `tests/conftest.py`:

```python
import pytest
from unittest.mock import MagicMock
from src.core.state import StateManager
from src.core.config import Config
from src.plugins.base import LLMPlugin

@pytest.fixture
def mock_llm():
    """Mock LLM plugin for NL tests."""
    llm = MagicMock(spec=LLMPlugin)
    # Default response: valid entity extraction
    llm.send_prompt.return_value = json.dumps({
        "entity_type": "project",
        "entities": [{"id": 1, "name": "Test Project"}],
        "confidence": 0.95
    })
    return llm

@pytest.fixture
def mock_state_nl(tmp_path):
    """StateManager with test database for NL tests."""
    db_path = tmp_path / "nl_test.db"
    state = StateManager(f"sqlite:///{db_path}")
    state.initialize()

    # Create test project
    project = state.create_project("Test Project", "/tmp/test")
    state.set_current_project(project.id)

    yield state

    # Cleanup
    state.close()

@pytest.fixture
def nl_config(tmp_path):
    """Config for NL tests."""
    config = Config.load()
    config.set('testing.mode', True)
    config.set('llm.timeout', 5.0)  # Fast timeout for tests
    return config
```

### Step 2: Implement Critical Bug Test (15 minutes)

Create `tests/test_nl_entity_extractor.py` with the bug prevention test first:

```python
import pytest
import json
from src.nl.entity_extractor import EntityExtractor, EntityExtractionException

class TestEntityTypeValidation:
    """Test entity_type validation to prevent regression of the None bug."""

    def test_entity_type_none_raises_exception(self, mock_llm, mock_state_nl, nl_config):
        """CRITICAL: Prevent entity_type=None bug (2025-11-11).

        Bug Log:
        ValueError: Invalid entity_type: None. Must be one of
        ['epic', 'story', 'task', 'subtask', 'milestone']

        Expected: EntityExtractionException with user-friendly message
        """
        # Setup: Mock LLM returns entity_type=None
        mock_llm.send_prompt.return_value = json.dumps({
            "entity_type": None,
            "entities": []
        })

        extractor = EntityExtractor(mock_llm, mock_state_nl, nl_config)

        # Execute and verify exception
        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("What is the current project?", "COMMAND")

        # Verify user-friendly error message
        error_msg = str(exc_info.value).lower()
        assert "couldn't determine" in error_msg or "invalid entity" in error_msg
        assert "project" in error_msg  # Suggest valid types

        # Verify NO Python traceback in message
        assert "valueerror" not in error_msg
        assert "traceback" not in error_msg

    def test_entity_type_missing_field(self, mock_llm, mock_state_nl, nl_config):
        """Should handle when entity_type field is completely missing."""
        mock_llm.send_prompt.return_value = json.dumps({
            "entities": []  # Missing entity_type field entirely
        })

        extractor = EntityExtractor(mock_llm, mock_state_nl, nl_config)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Show project", "COMMAND")
```

### Step 3: Run Initial Tests (5 minutes)

```bash
# Run just the bug prevention test
pytest tests/test_nl_entity_extractor.py::TestEntityTypeValidation::test_entity_type_none_raises_exception -v

# Expected: FAIL (because entity_extractor.py doesn't handle None gracefully yet)

# Fix the bug in src/nl/entity_extractor.py, then re-run
# Expected: PASS
```

### Step 4: Expand Coverage (3-4 hours)

Continue implementing the remaining tests in Phase 1:
1. Complete `test_nl_entity_extractor.py` (50 tests)
2. Implement `test_nl_intent_classifier.py` (30 tests)
3. Implement `test_nl_command_processor.py` (40 tests)

---

## Success Criteria

### Phase 1 Complete When:
- ✅ All 120 Phase 1 tests pass
- ✅ Coverage ≥70% for `src/nl/*.py`
- ✅ The `entity_type=None` bug test passes
- ✅ CI/CD pipeline includes NL tests

### Phase 2 Complete When:
- ✅ All 225 Phase 1+2 tests pass
- ✅ Coverage ≥85% for `src/nl/*.py`
- ✅ All 14 primary user stories have test coverage

### Phase 3 Complete When:
- ✅ All 300+ tests pass
- ✅ Coverage ≥90% for `src/nl/*.py`
- ✅ All 20 user stories validated end-to-end
- ✅ Edge case coverage ≥80%

---

## Test Guidelines Compliance

Every test MUST follow `docs/development/TEST_GUIDELINES.md`:

### ⚠️ Resource Limits
- Max sleep per test: 0.5s
- Max threads per test: 5
- Max memory per test: 20KB
- Mark slow tests: `@pytest.mark.slow`

### ✅ Mocking Strategy
- Mock all LLM calls (don't hit Ollama)
- Use in-memory SQLite for StateManager
- Mock agent communication
- Mock file I/O

### ✅ Test Isolation
- Each test creates its own StateManager instance
- Use `tmp_path` fixture for temporary files
- No shared state between tests
- Clean up resources in teardown

---

## Continuous Integration

Add to `.github/workflows/tests.yml`:

```yaml
- name: Run NL Command Tests
  run: |
    pytest tests/test_nl_*.py \
      --cov=src/nl \
      --cov-report=term \
      --cov-report=xml \
      --cov-fail-under=85 \
      -v
```

---

**Next Action:** Run `pytest tests/test_nl_entity_extractor.py -v` to start Phase 1 implementation.

**Estimated Time to First Pass:** 30 minutes (fixtures + bug test + fix)

**Estimated Time to 85% Coverage:** 12-15 hours (all 3 phases)
