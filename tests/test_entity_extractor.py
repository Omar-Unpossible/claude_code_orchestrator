"""Unit tests for Entity Extractor.

Tests the EntityExtractor with real LLM (Ollama/Qwen) to ensure:
- Accurate epic entity extraction
- Accurate story entity extraction with epic references
- Accurate task entity extraction
- Multi-item extraction ("create 3 stories...")
- Schema validation

Coverage Target: 95%
"""

import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

from src.nl.entity_extractor import (
    EntityExtractor,
    ExtractedEntities,
    EntityExtractionException
)
from src.plugins.registry import LLMRegistry


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def llm_plugin():
    """Get real LLM plugin (Ollama) for testing."""
    try:
        llm_class = LLMRegistry.get('ollama')
        llm = llm_class()

        config = {
            'model': 'qwen2.5-coder:32b',
            'endpoint': 'http://172.29.144.1:11434',
            'temperature': 0.2,
            'timeout': 30
        }
        llm.initialize(config)

        if not llm.is_available():
            pytest.skip("Ollama LLM not available - skipping real LLM tests")

        return llm
    except Exception as e:
        pytest.skip(f"Failed to initialize LLM: {e}")


@pytest.fixture
def extractor(llm_plugin):
    """Create EntityExtractor with real LLM."""
    return EntityExtractor(llm_plugin)


@pytest.fixture
def mock_llm_plugin():
    """Create mock LLM plugin for testing error cases."""
    mock_llm = Mock()
    mock_llm.generate = Mock()
    mock_llm.is_available = Mock(return_value=True)
    return mock_llm


# ============================================================================
# Test: Initialization
# ============================================================================

def test_init_with_default_paths(llm_plugin):
    """Test initialization with default schema and template paths."""
    extractor = EntityExtractor(llm_plugin)
    assert extractor.llm_plugin == llm_plugin
    assert extractor.schema is not None
    assert extractor.template is not None
    assert 'definitions' in extractor.schema  # Verify schema loaded


def test_init_with_custom_schema_path(llm_plugin):
    """Test initialization with custom schema path."""
    schema_path = Path(__file__).parent.parent / 'src/nl/schemas/obra_schema.json'
    extractor = EntityExtractor(llm_plugin, schema_path=schema_path)
    assert extractor.schema is not None


def test_init_with_missing_schema(llm_plugin, tmp_path):
    """Test initialization fails when schema not found."""
    bad_schema_path = tmp_path / 'nonexistent.json'
    with pytest.raises(EntityExtractionException, match="schema not found"):
        EntityExtractor(llm_plugin, schema_path=bad_schema_path)


def test_init_with_invalid_schema_json(llm_plugin, tmp_path):
    """Test initialization fails with invalid JSON schema."""
    bad_schema = tmp_path / 'bad_schema.json'
    bad_schema.write_text("{ invalid json }")

    with pytest.raises(EntityExtractionException, match="Invalid JSON"):
        EntityExtractor(llm_plugin, schema_path=bad_schema)


# ============================================================================
# Test: Epic Entity Extraction (TC-EE-001)
# ============================================================================

def test_epic_extraction_simple(extractor):
    """Test extraction of simple epic (TC-EE-001).

    Passing Criteria:
    - Extracts epic title accurately
    - Returns entity_type='epic'
    - Confidence score provided
    """
    message = "Create an epic called User Authentication"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "epic"
    assert len(result.entities) == 1
    assert result.entities[0]['title'] == "User Authentication"
    assert result.confidence > 0.0


def test_epic_extraction_with_description(extractor):
    """Test epic extraction with detailed description.

    Passing Criteria:
    - Extracts epic title
    - Extracts description with details
    - Returns confidence score
    """
    message = (
        "Create an epic called User Authentication System with description "
        "'Complete auth system with OAuth, MFA, and session management'"
    )
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "epic"
    assert len(result.entities) == 1
    assert "User Authentication" in result.entities[0]['title']
    assert 'description' in result.entities[0]
    # Check that description contains key concepts
    desc = result.entities[0]['description'].lower()
    assert any(word in desc for word in ['oauth', 'mfa', 'auth'])


def test_epic_extraction_with_priority(extractor):
    """Test epic extraction with priority keyword."""
    message = "Create high priority epic for Payment Processing"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "epic"
    assert len(result.entities) == 1
    assert "Payment Processing" in result.entities[0]['title']
    # Priority should be extracted (high=3)
    if 'priority' in result.entities[0]:
        assert result.entities[0]['priority'] in [1, 2, 3]  # high priority range


# ============================================================================
# Test: Story Entity Extraction (TC-EE-002)
# ============================================================================

def test_story_extraction_simple(extractor):
    """Test extraction of simple story."""
    message = "Add a story for user login"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "story"
    assert len(result.entities) == 1
    assert "login" in result.entities[0]['title'].lower()


def test_story_extraction_with_epic_reference(extractor):
    """Test story extraction with epic reference (TC-EE-002).

    Passing Criteria:
    - Extracts story details
    - Identifies epic reference (by name)
    """
    message = "Add a story for user login to the User Authentication epic"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "story"
    assert len(result.entities) == 1
    assert "login" in result.entities[0]['title'].lower()

    # Should have epic_reference or epic_id
    has_epic_ref = (
        'epic_reference' in result.entities[0] or
        'epic_id' in result.entities[0]
    )
    assert has_epic_ref, f"Missing epic reference in: {result.entities[0]}"


def test_story_extraction_with_epic_id(extractor):
    """Test story extraction with numeric epic ID."""
    message = "Add story for user signup to epic 5"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "story"
    assert len(result.entities) == 1

    # Should extract epic_id as integer
    if 'epic_id' in result.entities[0]:
        assert result.entities[0]['epic_id'] == 5


def test_story_extraction_user_story_format(extractor):
    """Test extraction of story in user story format."""
    message = "As a user, I want to log in with email/password so that I can access the system"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "story"
    assert len(result.entities) == 1
    # Should extract some title
    assert len(result.entities[0]['title']) > 0
    # Description should contain the user story
    if 'description' in result.entities[0]:
        assert "as a user" in result.entities[0]['description'].lower()


# ============================================================================
# Test: Multi-Item Extraction (TC-EE-003)
# ============================================================================

def test_multi_item_extraction_with_count(extractor):
    """Test extraction of multiple entities with count (TC-EE-003).

    Passing Criteria:
    - Extracts correct number of entities (count=3)
    - Applies common properties to all
    - Preserves individual titles
    """
    message = "Add 3 stories to User Auth epic: login, signup, and MFA"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "story"
    assert len(result.entities) == 3, \
        f"Expected 3 entities, got {len(result.entities)}"

    # Check titles
    titles = [e['title'].lower() for e in result.entities]
    assert any('login' in t for t in titles), f"Missing 'login' in titles: {titles}"
    assert any('signup' in t or 'sign' in t for t in titles), \
        f"Missing 'signup' in titles: {titles}"
    assert any('mfa' in t or 'factor' in t for t in titles), \
        f"Missing 'MFA' in titles: {titles}"

    # All should have epic reference
    for entity in result.entities:
        has_epic_ref = 'epic_reference' in entity or 'epic_id' in entity
        assert has_epic_ref, f"Entity missing epic reference: {entity}"


def test_multi_item_extraction_without_explicit_count(extractor):
    """Test extraction of multiple items from list without explicit count."""
    message = "Create stories for the Admin Dashboard epic: user management, settings, and reports"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "story"
    # Should extract 3 stories even without "3 stories"
    assert len(result.entities) >= 2, "Should extract multiple stories from list"


# ============================================================================
# Test: Task Entity Extraction
# ============================================================================

def test_task_extraction_simple(extractor):
    """Test extraction of simple task."""
    message = "Create task: Implement password hashing"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "task"
    assert len(result.entities) == 1
    assert "password" in result.entities[0]['title'].lower()
    assert "hash" in result.entities[0]['title'].lower()


def test_task_extraction_with_story_reference(extractor):
    """Test task extraction with story reference."""
    message = "Add task 'Create login API endpoint' to User Login story"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "task"
    assert len(result.entities) == 1
    assert "login" in result.entities[0]['title'].lower()

    # Should have story reference
    has_story_ref = (
        'story_reference' in result.entities[0] or
        'story_id' in result.entities[0]
    )
    assert has_story_ref


def test_task_extraction_with_dependencies(extractor):
    """Test task extraction with dependencies."""
    message = "Create task 'Integration testing' that depends on tasks 5 and 6"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "task"
    assert len(result.entities) == 1

    # Should extract dependencies
    if 'dependencies' in result.entities[0]:
        deps = result.entities[0]['dependencies']
        assert isinstance(deps, list)
        assert 5 in deps or 6 in deps


# ============================================================================
# Test: Subtask Entity Extraction
# ============================================================================

def test_subtask_extraction(extractor):
    """Test extraction of subtask with parent task ID."""
    message = "Add subtask to task 7: Write unit tests for password validation"
    result = extractor.extract(message, intent="COMMAND")

    assert result.entity_type == "subtask"
    assert len(result.entities) == 1
    assert "test" in result.entities[0]['title'].lower()

    # Must have parent_task_id for subtasks
    assert 'parent_task_id' in result.entities[0]
    assert result.entities[0]['parent_task_id'] == 7


# ============================================================================
# Test: Schema Validation
# ============================================================================

def test_schema_validation_epic_requires_title(extractor):
    """Test schema validation ensures epic has title."""
    # Create entity without title
    entity = {"description": "Test epic without title"}

    is_valid = extractor.validate_entity(entity, "epic")
    assert is_valid is False


def test_schema_validation_subtask_requires_parent(extractor):
    """Test schema validation ensures subtask has parent_task_id."""
    # Subtask without parent_task_id
    entity = {"title": "Test subtask"}

    is_valid = extractor.validate_entity(entity, "subtask")
    assert is_valid is False


def test_schema_validation_valid_epic(extractor):
    """Test schema validation accepts valid epic."""
    entity = {"title": "Valid Epic", "description": "Description"}

    is_valid = extractor.validate_entity(entity, "epic")
    assert is_valid is True


# ============================================================================
# Test: JSON Parsing Robustness
# ============================================================================

def test_parse_clean_json(extractor):
    """Test parsing clean JSON response."""
    json_response = json.dumps({
        "entity_type": "epic",
        "entities": [{"title": "Test Epic"}],
        "confidence": 0.95,
        "reasoning": "Clear epic"
    })

    parsed = extractor._parse_llm_response(json_response)
    assert parsed['entity_type'] == 'epic'
    assert len(parsed['entities']) == 1


def test_parse_json_in_markdown(extractor):
    """Test parsing JSON in markdown code blocks."""
    markdown_response = """```json
{
  "entity_type": "story",
  "entities": [{"title": "Test Story"}],
  "confidence": 0.90
}
```"""

    parsed = extractor._parse_llm_response(markdown_response)
    assert parsed['entity_type'] == 'story'


def test_parse_invalid_json(extractor):
    """Test parsing fails with invalid JSON."""
    invalid_response = "Not JSON at all"

    with pytest.raises(ValueError, match="Invalid JSON"):
        extractor._parse_llm_response(invalid_response)


def test_parse_missing_entity_type(extractor):
    """Test parsing fails when entity_type missing."""
    incomplete = json.dumps({
        "entities": [{"title": "Test"}]
        # Missing entity_type
    })

    with pytest.raises(ValueError, match="Missing required fields"):
        extractor._parse_llm_response(incomplete)


def test_parse_invalid_entity_type(extractor):
    """Test parsing fails with invalid entity_type."""
    invalid_type = json.dumps({
        "entity_type": "invalid_type",
        "entities": []
    })

    with pytest.raises(ValueError, match="Invalid entity_type"):
        extractor._parse_llm_response(invalid_type)


def test_parse_entities_not_list(extractor):
    """Test parsing fails when entities is not a list."""
    bad_entities = json.dumps({
        "entity_type": "epic",
        "entities": "should be a list"
    })

    with pytest.raises(ValueError, match="entities must be a list"):
        extractor._parse_llm_response(bad_entities)


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_extract_empty_message(extractor):
    """Test extraction fails gracefully with empty message."""
    with pytest.raises(EntityExtractionException, match="empty message"):
        extractor.extract("", intent="COMMAND")


def test_extract_whitespace_only(extractor):
    """Test extraction fails with whitespace-only message."""
    with pytest.raises(EntityExtractionException, match="empty message"):
        extractor.extract("   \n\t  ", intent="COMMAND")


def test_llm_generation_failure(mock_llm_plugin):
    """Test handling of LLM generation failure."""
    mock_llm_plugin.generate.side_effect = Exception("LLM API error")

    extractor = EntityExtractor(mock_llm_plugin)

    with pytest.raises(EntityExtractionException, match="LLM generation failed"):
        extractor.extract("Create an epic", intent="COMMAND")


def test_template_rendering_failure(mock_llm_plugin):
    """Test handling of template rendering failure."""
    extractor = EntityExtractor(mock_llm_plugin)

    with patch.object(extractor.template, 'render', side_effect=Exception("Template error")):
        with pytest.raises(EntityExtractionException, match="Failed to render"):
            extractor.extract("test message", intent="COMMAND")


# ============================================================================
# Test: ExtractedEntities Validation
# ============================================================================

def test_extracted_entities_creation():
    """Test ExtractedEntities dataclass creation."""
    result = ExtractedEntities(
        entity_type='epic',
        entities=[{'title': 'Test Epic'}],
        confidence=0.95,
        reasoning='Clear extraction'
    )

    assert result.entity_type == 'epic'
    assert len(result.entities) == 1
    assert result.confidence == 0.95


def test_extracted_entities_invalid_confidence():
    """Test ExtractedEntities rejects invalid confidence."""
    with pytest.raises(ValueError, match="Confidence must be between"):
        ExtractedEntities(entity_type='epic', confidence=1.5)


def test_extracted_entities_invalid_type():
    """Test ExtractedEntities rejects invalid entity_type."""
    with pytest.raises(ValueError, match="entity_type must be one of"):
        ExtractedEntities(entity_type='invalid_type')


def test_extracted_entities_default_values():
    """Test ExtractedEntities default values."""
    result = ExtractedEntities(entity_type='story')

    assert result.entities == []
    assert result.confidence == 0.0
    assert result.reasoning == ""


# ============================================================================
# Test: Context Awareness
# ============================================================================

def test_context_with_current_epic_id(extractor):
    """Test extraction uses context (current epic ID)."""
    context = {
        'current_epic_id': 5
    }

    message = "Add story for user login"
    result = extractor.extract(message, intent="COMMAND", context=context)

    # With context, might infer epic_id=5
    # This is optional behavior, not strictly required
    assert result.entity_type == "story"


def test_context_with_previous_turns(extractor):
    """Test extraction uses previous conversation turns."""
    context = {
        'previous_turns': [
            {'user_message': "Create epic User Authentication", 'intent': 'COMMAND'}
        ]
    }

    message = "Add 3 stories to it: login, signup, MFA"
    result = extractor.extract(message, intent="COMMAND", context=context)

    # Should understand "it" refers to epic from context
    assert result.entity_type == "story"
    assert len(result.entities) == 3


# ============================================================================
# Test: Integration Scenarios
# ============================================================================

def test_full_workflow_epic_creation(extractor):
    """Test complete workflow for epic creation."""
    message = "Create an epic called User Authentication with OAuth and MFA support, high priority"
    result = extractor.extract(message, intent="COMMAND")

    # Verify extraction
    assert result.entity_type == "epic"
    assert len(result.entities) == 1
    assert "Authentication" in result.entities[0]['title']
    assert result.confidence > 0.0
    assert len(result.reasoning) > 0


def test_batch_extraction(extractor):
    """Test extracting multiple messages in sequence."""
    messages = [
        ("Create epic for user auth", "epic"),
        ("Add story for login", "story"),
        ("Create task: implement password hashing", "task"),
    ]

    results = [
        extractor.extract(msg, intent="COMMAND")
        for msg, _ in messages
    ]

    # Verify all succeeded
    assert len(results) == 3
    assert results[0].entity_type == "epic"
    assert results[1].entity_type == "story"
    assert results[2].entity_type == "task"
