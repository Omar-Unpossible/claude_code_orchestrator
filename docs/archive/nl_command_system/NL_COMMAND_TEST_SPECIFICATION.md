# NL Command Interface - Test Specification

**Epic:** Natural Language Command Interface
**Specification:** NL_COMMAND_INTERFACE_SPEC.json
**Coverage Targets:** Unit 95%, Integration 90%, E2E 80%

---

## Test Strategy Overview

### Test Pyramid

```
                    ┌──────────────┐
                    │  E2E Tests   │  80% coverage
                    │  (Real LLM)  │  Full stack
                    └──────────────┘
                  ┌──────────────────┐
                  │ Integration Tests│  90% coverage
                  │ (Real LLM, Mock  │  Component interaction
                  │  StateManager)   │
                  └──────────────────┘
              ┌────────────────────────┐
              │      Unit Tests        │  95% coverage
              │   (All Mocked)         │  Individual components
              └────────────────────────┘
```

### Mock Strategy by Test Level

| Test Level | LLMPlugin | StateManager | Database | Context |
|------------|-----------|--------------|----------|---------|
| **Unit** | ✅ Mock | ✅ Mock | ✅ Mock | ✅ Mock |
| **Integration** | ❌ Real | ✅ Mock | ✅ Mock | ✅ Mock |
| **E2E** | ❌ Real | ❌ Real | ❌ Real (Test DB) | ❌ Real |

---

## Unit Tests (95% Coverage)

### 1. IntentClassifier Unit Tests
**File:** `tests/test_intent_classifier.py`
**Coverage Target:** 95%

#### Test Cases

##### TC-IC-001: Command Intent Detection
```python
def test_command_intent_detection(mock_llm_plugin):
    """Test classification of clear command intent."""
    # Setup
    classifier = IntentClassifier(mock_llm_plugin, confidence_threshold=0.7)
    mock_llm_plugin.generate.return_value = json.dumps({
        "intent": "COMMAND",
        "confidence": 0.95,
        "detected_entities": {"action": "create", "entity_type": "epic"}
    })

    # Execute
    result = classifier.classify("Create an epic called User Auth")

    # Assert
    assert result.intent == "COMMAND"
    assert result.confidence >= 0.9
    assert result.detected_entities["action"] == "create"
```

**Passing Criteria:**
- ✅ Returns COMMAND intent
- ✅ Confidence ≥0.9
- ✅ Detects basic entities (action, entity_type)

##### TC-IC-002: Question Intent Detection
```python
def test_question_intent_detection(mock_llm_plugin):
    """Test classification of question intent."""
    classifier = IntentClassifier(mock_llm_plugin)
    mock_llm_plugin.generate.return_value = json.dumps({
        "intent": "QUESTION",
        "confidence": 0.92
    })

    result = classifier.classify("How do I create an epic?")

    assert result.intent == "QUESTION"
    assert result.confidence >= 0.9
```

**Passing Criteria:**
- ✅ Returns QUESTION intent
- ✅ Confidence ≥0.9

##### TC-IC-003: Clarification Needed (Low Confidence)
```python
def test_clarification_needed_low_confidence(mock_llm_plugin):
    """Test CLARIFICATION_NEEDED when confidence below threshold."""
    classifier = IntentClassifier(mock_llm_plugin, confidence_threshold=0.7)
    mock_llm_plugin.generate.return_value = json.dumps({
        "intent": "COMMAND",
        "confidence": 0.55
    })

    result = classifier.classify("Maybe add something")

    assert result.intent == "CLARIFICATION_NEEDED"
    assert result.confidence < 0.7
```

**Passing Criteria:**
- ✅ Returns CLARIFICATION_NEEDED when confidence <0.7
- ✅ Respects confidence threshold parameter

##### TC-IC-004: Plugin Agnostic (Different LLM Providers)
```python
@pytest.mark.parametrize("provider", ["ollama", "openai", "claude"])
def test_plugin_agnostic(provider, mock_llm_registry):
    """Test IntentClassifier works with different LLM plugins."""
    llm_plugin = mock_llm_registry.get(provider)
    classifier = IntentClassifier(llm_plugin)

    # Each provider should work with same interface
    result = classifier.classify("Create epic")
    assert result.intent in ["COMMAND", "QUESTION", "CLARIFICATION_NEEDED"]
```

**Passing Criteria:**
- ✅ Works with Ollama (Qwen)
- ✅ Works with OpenAI
- ✅ Works with Claude (Anthropic)

##### TC-IC-005: Context Handling
```python
def test_context_aware_classification(mock_llm_plugin):
    """Test classification uses conversation context."""
    classifier = IntentClassifier(mock_llm_plugin)
    context = {
        "previous_turn": "I want to create an epic",
        "current_epic_id": 5
    }

    result = classifier.classify("Add 3 stories to it", context=context)

    # Should understand "it" refers to epic from context
    assert result.intent == "COMMAND"
    assert "epic_reference" in result.detected_entities
```

**Passing Criteria:**
- ✅ Uses conversation context for disambiguation
- ✅ Handles pronoun references ("it", "that")

---

### 2. EntityExtractor Unit Tests
**File:** `tests/test_entity_extractor.py`
**Coverage Target:** 95%

#### Test Cases

##### TC-EE-001: Epic Entity Extraction
```python
def test_epic_extraction(mock_llm_plugin, obra_schema):
    """Test extraction of epic details."""
    extractor = EntityExtractor(mock_llm_plugin, obra_schema)
    mock_llm_plugin.generate.return_value = json.dumps({
        "entity_type": "epic",
        "entities": [{
            "title": "User Authentication",
            "description": "Complete auth system with OAuth and MFA"
        }],
        "confidence": 0.93
    })

    result = extractor.extract(
        "Create an epic called User Authentication for a complete auth system with OAuth and MFA",
        intent="COMMAND"
    )

    assert result.entity_type == "epic"
    assert len(result.entities) == 1
    assert result.entities[0]["title"] == "User Authentication"
    assert "OAuth" in result.entities[0]["description"]
```

**Passing Criteria:**
- ✅ Extracts epic title accurately
- ✅ Extracts epic description with details
- ✅ Returns confidence score

##### TC-EE-002: Story Entity Extraction with Epic Reference
```python
def test_story_extraction_with_epic_reference(mock_llm_plugin, obra_schema):
    """Test extraction of story with epic reference."""
    extractor = EntityExtractor(mock_llm_plugin, obra_schema)
    mock_llm_plugin.generate.return_value = json.dumps({
        "entity_type": "story",
        "entities": [{
            "title": "User Login",
            "epic_reference": "User Authentication",
            "description": "As a user, I want to log in with email/password"
        }],
        "confidence": 0.91
    })

    result = extractor.extract(
        "Add a story for user login to the User Authentication epic",
        intent="COMMAND"
    )

    assert result.entity_type == "story"
    assert result.entities[0]["epic_reference"] == "User Authentication"
```

**Passing Criteria:**
- ✅ Extracts story details
- ✅ Identifies epic reference (by name or ID)
- ✅ Handles user story format

##### TC-EE-003: Multi-Item Extraction
```python
def test_multi_item_extraction(mock_llm_plugin, obra_schema):
    """Test extraction of multiple entities from one command."""
    extractor = EntityExtractor(mock_llm_plugin, obra_schema)
    mock_llm_plugin.generate.return_value = json.dumps({
        "entity_type": "story",
        "entities": [
            {"title": "User Login", "epic_reference": "User Auth"},
            {"title": "User Signup", "epic_reference": "User Auth"},
            {"title": "Multi-Factor Auth", "epic_reference": "User Auth"}
        ],
        "confidence": 0.88
    })

    result = extractor.extract(
        "Add 3 stories to User Auth epic: login, signup, and MFA",
        intent="COMMAND"
    )

    assert len(result.entities) == 3
    assert all(e["epic_reference"] == "User Auth" for e in result.entities)
```

**Passing Criteria:**
- ✅ Extracts multiple entities (count=3)
- ✅ Applies common properties (epic_reference) to all
- ✅ Preserves individual titles

##### TC-EE-004: Schema Validation
```python
def test_schema_validation(mock_llm_plugin, obra_schema):
    """Test that extracted entities match Obra schema."""
    extractor = EntityExtractor(mock_llm_plugin, obra_schema)

    # Attempt to extract with invalid field
    mock_llm_plugin.generate.return_value = json.dumps({
        "entity_type": "epic",
        "entities": [{
            "title": "Test Epic",
            "invalid_field": "should be rejected"
        }]
    })

    result = extractor.extract("Create epic", intent="COMMAND")

    # EntityExtractor should filter out invalid fields
    assert "invalid_field" not in result.entities[0]
```

**Passing Criteria:**
- ✅ Validates against Obra schema (obra_schema.json)
- ✅ Filters out invalid fields
- ✅ Ensures required fields present

---

### 3. CommandValidator Unit Tests
**File:** `tests/test_command_validator.py`
**Coverage Target:** 95%

#### Test Cases

##### TC-CV-001: Valid Epic Creation
```python
def test_valid_epic_creation(mock_state_manager):
    """Test validation of valid epic creation command."""
    validator = CommandValidator(mock_state_manager)
    entities = ExtractedEntities(
        entity_type="epic",
        entities=[{"title": "New Feature", "description": "A new feature"}],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is True
    assert len(result.errors) == 0
    assert result.validated_command["entity_type"] == "epic"
```

**Passing Criteria:**
- ✅ Validates successfully
- ✅ Returns validated_command dict
- ✅ No errors or warnings

##### TC-CV-002: Invalid Story Reference (Epic Doesn't Exist)
```python
def test_invalid_epic_reference(mock_state_manager):
    """Test validation catches non-existent epic reference."""
    validator = CommandValidator(mock_state_manager)
    mock_state_manager.get_epic.side_effect = EntityNotFoundError("Epic 9999 not found")

    entities = ExtractedEntities(
        entity_type="story",
        entities=[{"title": "Story", "epic_id": 9999}],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any("Epic 9999 not found" in err for err in result.errors)
```

**Passing Criteria:**
- ✅ Detects non-existent epic_id
- ✅ Returns meaningful error message
- ✅ valid=False

##### TC-CV-003: Circular Dependency Detection
```python
def test_circular_dependency_detection(mock_state_manager):
    """Test validation catches circular task dependencies."""
    validator = CommandValidator(mock_state_manager)

    # Task 1 depends on Task 2, Task 2 depends on Task 1
    entities = ExtractedEntities(
        entity_type="task",
        entities=[
            {"id": 1, "title": "Task 1", "dependencies": [2]},
            {"id": 2, "title": "Task 2", "dependencies": [1]}
        ],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any("circular dependency" in err.lower() for err in result.errors)
```

**Passing Criteria:**
- ✅ Detects circular dependencies
- ✅ Returns error describing cycle
- ✅ valid=False

##### TC-CV-004: Required Fields Validation
```python
def test_required_fields_validation(mock_state_manager):
    """Test validation ensures required fields are present."""
    validator = CommandValidator(mock_state_manager)

    entities = ExtractedEntities(
        entity_type="epic",
        entities=[{"description": "Missing title!"}],  # title required
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any("title" in err.lower() for err in result.errors)
```

**Passing Criteria:**
- ✅ Checks required fields (title, description)
- ✅ Returns specific error for missing field
- ✅ valid=False

---

### 4. CommandExecutor Unit Tests
**File:** `tests/test_command_executor.py`
**Coverage Target:** 95%

#### Test Cases

##### TC-CE-001: Epic Creation Execution
```python
def test_epic_creation_execution(mock_state_manager):
    """Test successful epic creation via StateManager."""
    executor = CommandExecutor(mock_state_manager)
    mock_state_manager.create_epic.return_value = 5  # Epic ID

    command = {
        "entity_type": "epic",
        "title": "User Auth",
        "description": "Authentication system"
    }

    result = executor.execute(command)

    assert result.success is True
    assert 5 in result.created_ids
    mock_state_manager.create_epic.assert_called_once()
```

**Passing Criteria:**
- ✅ Calls StateManager.create_epic()
- ✅ Returns created epic ID
- ✅ success=True

##### TC-CE-002: Transaction Rollback on Error
```python
def test_transaction_rollback_on_error(mock_state_manager):
    """Test rollback when execution fails."""
    executor = CommandExecutor(mock_state_manager)
    mock_state_manager.create_epic.side_effect = DatabaseError("DB connection lost")

    command = {"entity_type": "epic", "title": "Test"}

    result = executor.execute(command)

    assert result.success is False
    assert "DB connection lost" in result.errors[0]
    mock_state_manager.rollback.assert_called_once()
```

**Passing Criteria:**
- ✅ Catches execution errors
- ✅ Calls rollback() on StateManager
- ✅ Returns error in result

##### TC-CE-003: Confirmation Required for Destructive Ops
```python
def test_confirmation_required_for_delete(mock_state_manager):
    """Test confirmation prompt for destructive operations."""
    executor = CommandExecutor(mock_state_manager)

    command = {
        "entity_type": "epic",
        "action": "delete",
        "epic_id": 5
    }

    result = executor.execute(command)

    # Should NOT execute without confirmation
    assert result.success is False
    assert "confirmation_required" in result.errors[0].lower()
    mock_state_manager.delete_epic.assert_not_called()
```

**Passing Criteria:**
- ✅ Detects destructive operation (delete, update)
- ✅ Requires confirmation before execution
- ✅ Does not execute without confirmation

---

### 5. ResponseFormatter Unit Tests
**File:** `tests/test_response_formatter.py`
**Coverage Target:** 95%

#### Test Cases

##### TC-RF-001: Success Response Formatting
```python
def test_success_response_formatting():
    """Test formatting of successful execution result."""
    formatter = ResponseFormatter()

    result = ExecutionResult(
        success=True,
        created_ids=[5],
        results={"epic_title": "User Auth"}
    )

    response = formatter.format(result, intent="COMMAND")

    assert "✓" in response  # Success checkmark
    assert "Epic #5" in response
    assert "User Auth" in response
```

**Passing Criteria:**
- ✅ Includes success indicator (✓)
- ✅ Shows created IDs
- ✅ Suggests next actions

##### TC-RF-002: Error Response Formatting
```python
def test_error_response_formatting():
    """Test formatting of error result."""
    formatter = ResponseFormatter()

    result = ExecutionResult(
        success=False,
        errors=["Epic not found"]
    )

    response = formatter.format(result, intent="COMMAND")

    assert "✗" in response  # Error indicator
    assert "Epic not found" in response
    assert "Try" in response  # Suggests recovery
```

**Passing Criteria:**
- ✅ Includes error indicator (✗)
- ✅ Shows error message
- ✅ Suggests recovery action

##### TC-RF-003: Color Coding
```python
def test_color_coding():
    """Test colorama integration for colored output."""
    formatter = ResponseFormatter()

    success_result = ExecutionResult(success=True, created_ids=[1])
    error_result = ExecutionResult(success=False, errors=["Error"])

    success_response = formatter.format(success_result, intent="COMMAND")
    error_response = formatter.format(error_result, intent="COMMAND")

    # Check for ANSI color codes
    assert "\033[92m" in success_response  # Green
    assert "\033[91m" in error_response    # Red
```

**Passing Criteria:**
- ✅ Green color for success
- ✅ Red color for errors
- ✅ Yellow color for warnings

---

### 6. NLCommandProcessor Unit Tests
**File:** `tests/test_nl_command_processor.py`
**Coverage Target:** 95%

#### Test Cases

##### TC-NL-001: Full Pipeline (Command)
```python
def test_full_pipeline_command(mock_llm_plugin, mock_state_manager):
    """Test complete pipeline for command execution."""
    processor = NLCommandProcessor(mock_llm_plugin, mock_state_manager, config)

    # Mock LLM responses
    mock_llm_plugin.generate.side_effect = [
        json.dumps({"intent": "COMMAND", "confidence": 0.95}),  # Intent
        json.dumps({"entity_type": "epic", "entities": [{"title": "Test"}]})  # Extract
    ]
    mock_state_manager.create_epic.return_value = 5

    result = processor.process("Create an epic called Test")

    assert result.success is True
    assert result.intent == "COMMAND"
    assert "Epic #5" in result.response
```

**Passing Criteria:**
- ✅ Calls IntentClassifier
- ✅ Calls EntityExtractor
- ✅ Calls CommandValidator
- ✅ Calls CommandExecutor
- ✅ Returns formatted response

##### TC-NL-002: Full Pipeline (Question)
```python
def test_full_pipeline_question(mock_llm_plugin):
    """Test pipeline routes questions to Claude Code."""
    processor = NLCommandProcessor(mock_llm_plugin, mock_state_manager, config)

    mock_llm_plugin.generate.return_value = json.dumps({
        "intent": "QUESTION",
        "confidence": 0.93
    })

    result = processor.process("How do I create an epic?")

    assert result.intent == "QUESTION"
    # Should forward to Claude Code for informational response
    assert result.forwarded_to_claude is True
```

**Passing Criteria:**
- ✅ Detects QUESTION intent
- ✅ Forwards to Claude Code
- ✅ Does not execute commands

---

## Integration Tests (90% Coverage)

### File: `tests/integration/test_nl_pipeline.py`

#### TC-INT-001: Intent → Extract → Validate → Execute
```python
def test_full_nl_pipeline_integration(real_llm_plugin, mock_db):
    """Integration test with real LLM, mocked StateManager."""
    processor = NLCommandProcessor(real_llm_plugin, mock_state_manager, config)

    response = processor.process(
        "Create an epic for user authentication with OAuth and MFA support"
    )

    # Real LLM should classify as COMMAND
    assert response.intent == "COMMAND"
    # Real LLM should extract epic details
    assert response.success is True
    # StateManager create_epic should be called
    mock_state_manager.create_epic.assert_called_once()
```

**Passing Criteria:**
- ✅ Real LLM classifies intent correctly
- ✅ Real LLM extracts entities accurately
- ✅ Validation passes
- ✅ Execution called with correct params

---

## E2E Tests (80% Coverage)

### File: `tests/e2e/test_nl_interactive_mode.py`

#### TC-E2E-001: Create Epic + Stories (Multi-Turn)
```python
def test_create_epic_and_stories_e2e(test_db, real_llm):
    """E2E test: Create epic, then add stories in conversation."""
    # Start interactive mode with test DB
    session = InteractiveSession(test_db, real_llm)

    # Turn 1: Create epic
    response1 = session.send("Create an epic for user authentication")
    assert "Epic #" in response1
    epic_id = extract_id_from_response(response1)

    # Turn 2: Add stories (context-aware)
    response2 = session.send("Add 3 stories: login, signup, MFA")
    assert "3 stories" in response2

    # Verify in database
    epic = test_db.get_epic(epic_id)
    stories = test_db.get_epic_stories(epic_id)
    assert len(stories) == 3
```

**Passing Criteria:**
- ✅ Epic created in real database
- ✅ Stories linked to epic correctly
- ✅ Context preserved across turns
- ✅ End-to-end latency <5s

---

## Performance Benchmarks

### Latency Targets (P95)

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Intent Classification | <2s | Time from process() call to IntentResult |
| Entity Extraction | <2.5s | Time from extract() call to ExtractedEntities |
| End-to-End Pipeline | <3s | Time from process() to formatted response |

### Accuracy Targets

| Component | Target | Measurement |
|-----------|--------|-------------|
| Intent Classification | >95% | % correct on 50-sample test set |
| Entity Extraction | >90% | % accurate entities on 100-sample test set |
| End-to-End Success | >85% | % commands that execute successfully |

---

## Test Data Requirements

### Intent Classification Test Set (50 samples)
- 20 COMMAND examples (create, update, delete, list, execute)
- 20 QUESTION examples (how, what, why, when, show me)
- 10 CLARIFICATION_NEEDED examples (ambiguous, vague, incomplete)

### Entity Extraction Test Set (100 samples)
- 30 Epic creation commands (various formats)
- 30 Story creation commands (with/without epic references)
- 20 Task creation commands (with story/epic references)
- 10 Multi-item commands (create N entities)
- 10 Edge cases (special characters, long text, etc.)

### Validation Edge Cases (30 samples)
- Non-existent references (epic_id, story_id)
- Circular dependencies
- Missing required fields
- Invalid field types
- Duplicate titles

---

## Running Tests

### Unit Tests
```bash
# All unit tests
pytest tests/test_*.py -v --cov=src/nl --cov-report=term

# Specific component
pytest tests/test_intent_classifier.py -v
pytest tests/test_entity_extractor.py -v

# With coverage report
pytest tests/test_*.py --cov=src/nl --cov-report=html
```

### Integration Tests
```bash
# All integration tests (requires real LLM)
pytest tests/integration/ -v

# Specific integration test
pytest tests/integration/test_nl_pipeline.py::test_full_nl_pipeline_integration -v
```

### E2E Tests
```bash
# All E2E tests (requires real LLM + test DB)
pytest tests/e2e/ -v --slow

# Specific E2E scenario
pytest tests/e2e/test_nl_interactive_mode.py::test_create_epic_and_stories_e2e -v
```

### Performance Tests
```bash
# Run performance benchmarks
pytest tests/performance/test_nl_latency.py -v

# Generate performance report
pytest tests/performance/ --benchmark-only --benchmark-json=perf_report.json
```

---

## Success Criteria Summary

### Must Pass (Blocker)
- ✅ All unit tests pass (95% coverage)
- ✅ All integration tests pass (90% coverage)
- ✅ Intent classification accuracy >90%
- ✅ Entity extraction accuracy >85%
- ✅ No critical bugs (P0)

### Should Pass (High Priority)
- ✅ E2E tests pass (80% coverage)
- ✅ P95 latency <3s
- ✅ Intent classification accuracy >95%
- ✅ Entity extraction accuracy >90%

### Nice to Have
- ✅ Performance benchmarks documented
- ✅ Test data sets versioned and reusable
- ✅ Automated regression testing in CI/CD

---

**Questions on test approach?** Update this specification or consult with the team.

**Ready to implement tests?** Follow test case specifications above for each component.
