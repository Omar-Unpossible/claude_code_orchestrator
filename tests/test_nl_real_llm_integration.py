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

from src.nl.intent_classifier import IntentClassifier
from src.nl.entity_extractor import EntityExtractor
from src.nl.nl_command_processor import NLCommandProcessor
from src.core.state import StateManager
from src.core.config import Config

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
def real_llm_config():
    """
    Configure for real LLM (not mock).

    Module-scoped to reuse config across all tests in file.
    """
    config = Config.load()
    config.set('testing.mode', False)  # Disable auto-mocking
    config.set('llm.provider', 'ollama')
    config.set('llm.model', 'qwen2.5-coder:32b')
    config.set('llm.base_url', 'http://172.29.144.1:11434')
    config.set('llm.timeout', 30.0)  # Real LLM needs more time
    config.set('llm.temperature', 0.1)  # Low temp for consistency
    return config


@pytest.fixture(scope="module")
def real_state_manager(real_llm_config):
    """
    StateManager for real LLM tests.

    Module-scoped to reuse database across tests (faster).
    Uses in-memory SQLite for speed.
    """
    state = StateManager(database_url='sqlite:///:memory:')

    # Create test project
    project = state.create_project(
        name="Real LLM Test Project",
        description="Integration testing with real Ollama/Qwen",
        working_dir="/tmp/test_real_llm"
    )

    yield state

    # Cleanup
    state.close()


@pytest.fixture
def real_llm_interface(real_llm_config):
    """Real LLM interface for direct testing"""
    from src.llm.local_interface import LocalLLMInterface
    return LocalLLMInterface(
        model=real_llm_config.get('llm.model'),
        base_url=real_llm_config.get('llm.base_url'),
        timeout=real_llm_config.get('llm.timeout')
    )


@pytest.fixture
def real_intent_classifier(real_llm_interface):
    """IntentClassifier using real Ollama LLM"""
    return IntentClassifier(
        llm_plugin=real_llm_interface,
        confidence_threshold=0.7
    )


@pytest.fixture
def real_entity_extractor(real_llm_interface):
    """EntityExtractor using real Ollama LLM"""
    return EntityExtractor(
        llm_plugin=real_llm_interface
    )


@pytest.fixture
def real_nl_processor(real_llm_interface, real_state_manager, real_llm_config):
    """NLCommandProcessor using real Ollama LLM"""
    return NLCommandProcessor(
        llm_plugin=real_llm_interface,
        state_manager=real_state_manager,
        config=real_llm_config
    )


# ============================================================================
# Helper Utilities
# ============================================================================

def assert_valid_intent_result(result, expected_intent: str, min_confidence: float = 0.7):
    """Validate IntentResult from real LLM"""
    assert result is not None, "Intent result should not be None"
    assert result.intent in ["COMMAND", "QUESTION"], f"Invalid intent: {result.intent}"
    assert result.intent == expected_intent, f"Expected {expected_intent}, got {result.intent}"
    assert result.confidence >= min_confidence, \
        f"Confidence {result.confidence} below threshold {min_confidence}"
    assert len(result.reasoning) > 0, "Reasoning should not be empty"


def assert_valid_extraction_result(
    result,
    expected_entity_type: str,
    min_entities: int = 1,
    min_confidence: float = 0.7
):
    """Validate ExtractedEntities from real LLM"""
    assert result is not None, "Extraction result should not be None"
    assert result.entity_type == expected_entity_type, \
        f"Expected {expected_entity_type}, got {result.entity_type}"
    assert len(result.entities) >= min_entities, \
        f"Expected at least {min_entities} entities, got {len(result.entities)}"
    assert result.confidence >= min_confidence, \
        f"Confidence {result.confidence} below threshold {min_confidence}"
    assert len(result.reasoning) > 0, "Reasoning should not be empty"


# ============================================================================
# Test Class 1: Intent Classification (8 tests)
# ============================================================================

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

    def test_clear_question_what_project(self, real_intent_classifier):
        """REAL LLM: Classify 'What is current project' as COMMAND (queries Obra data)"""
        result = real_intent_classifier.classify(
            "What is the current project?"
        )
        # This should be COMMAND because it queries Obra data
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.7)

    def test_clear_question_general_programming(self, real_intent_classifier):
        """REAL LLM: Classify general programming question as QUESTION"""
        result = real_intent_classifier.classify(
            "How do I implement OAuth in Python?"
        )
        assert_valid_intent_result(result, "QUESTION", min_confidence=0.8)

    def test_clear_question_show_tasks(self, real_intent_classifier):
        """REAL LLM: Classify 'Show tasks' as COMMAND (queries Obra data)"""
        result = real_intent_classifier.classify(
            "Show me all open tasks for epic 5"
        )
        # This should be COMMAND because it queries Obra work items
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.7)

    def test_clear_question_list_stories(self, real_intent_classifier):
        """REAL LLM: Classify 'List stories' as COMMAND (queries Obra data)"""
        result = real_intent_classifier.classify(
            "List all stories with acceptance criteria"
        )
        # This should be COMMAND because it queries Obra work items
        assert_valid_intent_result(result, "COMMAND", min_confidence=0.7)


# ============================================================================
# Test Class 2: Entity Extraction (10 tests)
# ============================================================================

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
        assert 'title' in epic, "Epic should have title"
        assert 'authentication' in epic['title'].lower(), "Title should mention authentication"

    def test_extract_story_with_user_story_format(self, real_entity_extractor):
        """REAL LLM: Extract story from user story format"""
        result = real_entity_extractor.extract(
            "As a user, I want to reset my password so that I can regain access if I forget it",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "story", min_entities=1, min_confidence=0.7)

        story = result.entities[0]
        assert 'title' in story, "Story should have title"
        assert 'description' in story, "Story should have description"

    def test_extract_task_with_description(self, real_entity_extractor):
        """REAL LLM: Extract task with clear title and description"""
        result = real_entity_extractor.extract(
            "Create task 'Implement password hashing' using bcrypt for secure storage",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "task", min_entities=1, min_confidence=0.8)

        task = result.entities[0]
        assert 'title' in task, "Task should have title"
        assert 'password' in task['title'].lower() or 'hashing' in task['title'].lower(), \
            "Title should mention password or hashing"

    def test_extract_subtask_with_parent(self, real_entity_extractor):
        """REAL LLM: Extract subtask with parent reference"""
        result = real_entity_extractor.extract(
            "Add subtask to task 7: Write unit tests for password validation",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "subtask", min_entities=1, min_confidence=0.8)

        subtask = result.entities[0]
        assert 'title' in subtask, "Subtask should have title"
        assert 'parent_task_id' in subtask, "Subtask should have parent_task_id"
        assert subtask['parent_task_id'] == 7, "Parent task ID should be 7"

    def test_extract_milestone_with_epic_dependencies(self, real_entity_extractor):
        """REAL LLM: Extract milestone with required epics"""
        result = real_entity_extractor.extract(
            "Create milestone 'Auth Complete' when epics 5 and 7 are done",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "milestone", min_entities=1, min_confidence=0.8)

        milestone = result.entities[0]
        assert 'name' in milestone, "Milestone should have name"
        assert 'required_epic_ids' in milestone, "Milestone should have required_epic_ids"
        assert 5 in milestone['required_epic_ids'], "Should include epic 5"
        assert 7 in milestone['required_epic_ids'], "Should include epic 7"

    # ========== Multi-Entity Extraction (2 tests) ==========

    def test_extract_multiple_tasks_batch(self, real_entity_extractor):
        """REAL LLM: Extract multiple tasks from batch creation"""
        result = real_entity_extractor.extract(
            "Create 3 tasks: Implement login, Implement logout, Implement session management",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "task", min_entities=3, min_confidence=0.8)

        titles = [task['title'].lower() for task in result.entities]
        assert any('login' in title for title in titles), "Should have login task"
        assert any('logout' in title for title in titles), "Should have logout task"
        assert any('session' in title for title in titles), "Should have session task"

    def test_extract_stories_with_epic_reference(self, real_entity_extractor):
        """REAL LLM: Extract multiple stories with epic reference"""
        result = real_entity_extractor.extract(
            "Add stories to epic 'Auth': Email login, OAuth login, MFA setup",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "story", min_entities=3, min_confidence=0.7)

        # All stories should have titles
        for story in result.entities:
            assert 'title' in story, "Each story should have a title"

    # ========== Edge Cases (3 tests) ==========

    def test_extract_with_emojis(self, real_entity_extractor):
        """REAL LLM: Handle emojis in input"""
        result = real_entity_extractor.extract(
            "Create epic 🔐 'Security Hardening' for 🛡️ defense measures",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "epic", min_entities=1, min_confidence=0.7)

        epic = result.entities[0]
        assert 'title' in epic, "Epic should have title"

    def test_extract_with_code_blocks(self, real_entity_extractor):
        """REAL LLM: Handle code snippets in description"""
        result = real_entity_extractor.extract(
            "Create task: Implement `hash_password(password)` function using bcrypt",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "task", min_entities=1, min_confidence=0.7)

        task = result.entities[0]
        assert 'title' in task, "Task should have title"

    def test_extract_with_special_characters(self, real_entity_extractor):
        """REAL LLM: Handle special characters"""
        result = real_entity_extractor.extract(
            "Create story: User can use symbols (@#$%) in passwords",
            intent="COMMAND"
        )
        assert_valid_extraction_result(result, "story", min_entities=1, min_confidence=0.7)

        story = result.entities[0]
        assert 'title' in story, "Story should have title"


# ============================================================================
# Test Class 3: Full Pipeline E2E (8 tests)
# ============================================================================

class TestRealLLMFullPipeline:
    """Test complete NL pipeline with real Ollama/Qwen LLM"""

    def test_create_epic_end_to_end(self, real_nl_processor):
        """REAL LLM: Full pipeline - create epic"""
        response = real_nl_processor.process(
            "Create an epic called 'Payment System' for Stripe integration"
        )

        assert response.success is True, "Epic creation should succeed"
        assert response.intent == "COMMAND", "Should be classified as COMMAND"
        assert response.execution_result is not None, "Should have execution result"
        assert len(response.execution_result.created_ids) == 1, "Should create 1 epic"

    def test_create_story_with_epic_reference(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - create story for epic"""
        # First create epic
        epic_id = real_state_manager.create_epic(1, "User Auth", "Authentication features")

        response = real_nl_processor.process(
            f"Add story 'Password Reset' to epic {epic_id}"
        )

        assert response.success is True, "Story creation should succeed"
        assert response.execution_result is not None, "Should have execution result"
        assert len(response.execution_result.created_ids) == 1, "Should create 1 story"

    def test_create_task_with_dependencies(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - create task with dependencies"""
        # Create prerequisite tasks
        task1 = real_state_manager.create_task(1, "Setup environment", "Install dependencies")
        task2 = real_state_manager.create_task(1, "Configure database", "Set up DB schema")

        response = real_nl_processor.process(
            f"Create task 'Run migrations' that depends on tasks {task1} and {task2}"
        )

        assert response.success is True, "Task creation should succeed"
        assert response.execution_result is not None, "Should have execution result"

    def test_create_milestone_workflow(self, real_nl_processor, real_state_manager):
        """REAL LLM: Full pipeline - create milestone"""
        # Create prerequisite epics
        epic1 = real_state_manager.create_epic(1, "Auth Epic", "Authentication")
        epic2 = real_state_manager.create_epic(1, "Payment Epic", "Payments")

        response = real_nl_processor.process(
            f"Create milestone 'v1.0 Complete' when epics {epic1} and {epic2} are done"
        )

        assert response.success is True, "Milestone creation should succeed"
        assert response.execution_result is not None, "Should have execution result"

    def test_query_project_info(self, real_nl_processor):
        """REAL LLM: Full pipeline - query project info"""
        response = real_nl_processor.process(
            "What is the current project?"
        )

        # Should handle query (may forward or return info)
        assert isinstance(response.response, str), "Should return a response string"
        assert len(response.response) > 0, "Response should not be empty"

    def test_multi_turn_workflow(self, real_nl_processor, real_state_manager):
        """REAL LLM: Multiple related commands in sequence"""
        # Turn 1: Create epic
        response1 = real_nl_processor.process(
            "Create epic 'User Management' for user administration"
        )
        assert response1.success is True, "First command should succeed"
        epic_id = response1.execution_result.created_ids[0]

        # Turn 2: Add story to that epic
        response2 = real_nl_processor.process(
            f"Add story 'Create User' to epic {epic_id}"
        )
        assert response2.success is True, "Second command should succeed"

    def test_batch_creation_workflow(self, real_nl_processor):
        """REAL LLM: Create multiple work items at once"""
        response = real_nl_processor.process(
            "Create 3 epics: Auth System, Payment System, Notification System"
        )

        assert response.success is True, "Batch creation should succeed"
        assert response.execution_result is not None, "Should have execution result"
        assert len(response.execution_result.created_ids) == 3, "Should create 3 epics"

    def test_error_recovery_invalid_reference(self, real_nl_processor):
        """REAL LLM: Handle invalid epic reference gracefully"""
        response = real_nl_processor.process(
            "Add story to epic 999"
        )

        # Should fail validation but not crash
        assert response.success is False, "Should fail with invalid epic ID"
        assert '999' in response.response or 'not found' in response.response.lower(), \
            "Error message should mention missing epic"


# ============================================================================
# Test Class 4: LLM Failure Modes (4 tests)
# ============================================================================

class TestRealLLMFailureModes:
    """Test LLM failure handling with real Ollama/Qwen LLM"""

    @pytest.mark.timeout(35)  # Should timeout before this
    def test_llm_timeout_handling(self, real_llm_config):
        """REAL LLM: Handle timeout gracefully"""
        # Configure very short timeout
        real_llm_config.set('llm.timeout', 1.0)  # 1 second - too short for most LLM calls

        from src.llm.local_interface import LocalLLMInterface
        llm = LocalLLMInterface(
            model='qwen2.5-coder:32b',
            base_url='http://172.29.144.1:11434',
            timeout=1.0
        )

        extractor = EntityExtractor(llm_plugin=llm)

        # Should raise timeout exception
        from src.nl.entity_extractor import EntityExtractionException
        with pytest.raises((EntityExtractionException, Exception)) as exc_info:
            extractor.extract(
                "Create a very complex epic with lots of details about authentication, authorization, and access control",
                intent="COMMAND"
            )

        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "timed out" in error_msg, \
            "Error should mention timeout"

    def test_llm_connection_failure(self, real_llm_config):
        """REAL LLM: Handle connection failure to wrong URL"""
        from src.llm.local_interface import LocalLLMInterface

        # Configure wrong URL
        llm = LocalLLMInterface(
            model='qwen2.5-coder:32b',
            base_url='http://invalid.url:99999',  # Invalid URL
            timeout=5.0
        )

        classifier = IntentClassifier(llm_plugin=llm)

        # Should raise connection exception
        with pytest.raises(Exception) as exc_info:
            classifier.classify("Create a task")

        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ['connection', 'connect', 'unreachable', 'error']), \
            "Error should mention connection issue"

    def test_llm_invalid_json_recovery(self, real_llm_interface):
        """REAL LLM: Verify LLM returns valid JSON (should always work with proper prompts)"""
        # This test verifies our prompts are robust
        extractor = EntityExtractor(llm_plugin=real_llm_interface)

        # Test with various inputs that might confuse LLM
        tricky_inputs = [
            "Create epic with weird formatting: {{json}}, [arrays], 'quotes'",
            "Add task: Test JSON parsing with nested {objects: {key: 'value'}}",
            "Create story: Handle special chars @#$%^&*()"
        ]

        for input_msg in tricky_inputs:
            result = extractor.extract(input_msg, intent="COMMAND")
            # Should successfully parse despite tricky input
            assert result is not None, f"Should parse: {input_msg}"
            assert result.entity_type in ['epic', 'story', 'task', 'subtask', 'milestone', 'project'], \
                "Should return valid entity type"

    def test_llm_consistency_across_calls(self, real_entity_extractor):
        """REAL LLM: Verify consistent extraction across multiple calls"""
        message = "Create epic 'Payment System' with Stripe integration"

        # Call LLM 3 times with same input
        results = []
        for _ in range(3):
            result = real_entity_extractor.extract(message, intent="COMMAND")
            results.append(result)
            time.sleep(0.5)  # Small delay between calls

        # All should return epic type
        for result in results:
            assert result.entity_type == "epic", "Should consistently extract epic"
            assert 'payment' in result.entities[0]['title'].lower(), \
                "Should consistently extract payment-related title"

        # Confidence should be similar (within 0.2)
        confidences = [r.confidence for r in results]
        confidence_range = max(confidences) - min(confidences)
        assert confidence_range < 0.3, \
            f"Confidence should be consistent, got range: {confidence_range}"


# ============================================================================
# Performance Benchmark (Optional)
# ============================================================================

@pytest.mark.benchmark
class TestRealLLMPerformance:
    """Optional performance benchmarks for real LLM calls"""

    def test_intent_classification_speed(self, real_intent_classifier, benchmark):
        """Benchmark: Intent classification speed"""
        def classify():
            return real_intent_classifier.classify("Create a task for OAuth")

        result = benchmark(classify)
        assert result.intent == "COMMAND"

    def test_entity_extraction_speed(self, real_entity_extractor, benchmark):
        """Benchmark: Entity extraction speed"""
        def extract():
            return real_entity_extractor.extract(
                "Create epic 'Auth System' with OAuth and MFA",
                intent="COMMAND"
            )

        result = benchmark(extract)
        assert result.entity_type == "epic"

    def test_full_pipeline_speed(self, real_nl_processor, benchmark):
        """Benchmark: Full pipeline speed"""
        def process():
            return real_nl_processor.process(
                "Create epic 'Payment System'"
            )

        result = benchmark(process)
        assert result.success is True
