# ADR-016 Migration Guide: v1.3.0 → v1.6.0

**Version**: 1.0
**Date**: November 11, 2025
**Scope**: Natural Language Command Interface Architecture Refactor
**Breaking Changes**: Yes (EntityExtractor deprecated)

---

## Executive Summary

ADR-016 refactors the Natural Language Command Interface from a single-classifier approach (EntityExtractor) to a five-stage pipeline with dedicated components:

**Old Architecture (v1.3.0)**:
```
IntentClassifier → EntityExtractor → CommandValidator → CommandExecutor
```

**New Architecture (v1.6.0)**:
```
IntentClassifier → OperationClassifier → EntityTypeClassifier →
EntityIdentifierExtractor → ParameterExtractor → CommandValidator → CommandExecutor
```

**Result**: **95%+ accuracy** (up from 80-85%) through single-responsibility components and progressive refinement.

---

## Who Needs to Migrate?

### You MUST migrate if:

1. **You use EntityExtractor directly** in custom code
2. **You have tests using ExtractedEntities API**
3. **You access CommandValidator.validate_legacy()** explicitly
4. **You parse entity extraction responses** manually

### You DON'T need to migrate if:

1. **You only use the interactive CLI** (migration is transparent)
2. **You only use slash commands** (no NL interface usage)
3. **You use NLCommandProcessor** (updated automatically)
4. **You use high-level APIs** (e.g., `process_nl_command()`)

---

## Breaking Changes

### 1. EntityExtractor Deprecated

**Status**: Deprecated in v1.6.0, removed in v1.7.0

**Old Code (v1.3.0)**:
```python
from src.nl.entity_extractor import EntityExtractor, ExtractedEntities

extractor = EntityExtractor(llm_plugin)
result = extractor.extract(user_input, intent="COMMAND")

# Result: ExtractedEntities object
assert result.entity_type == "epic"
assert result.entities[0]["title"] == "User Authentication"
```

**New Code (v1.6.0)**:
```python
from src.nl.operation_classifier import OperationClassifier
from src.nl.entity_type_classifier import EntityTypeClassifier
from src.nl.entity_identifier_extractor import EntityIdentifierExtractor
from src.nl.parameter_extractor import ParameterExtractor
from src.nl.types import OperationContext, OperationType, EntityType

# Stage 1: Classify operation
operation_classifier = OperationClassifier(llm_plugin)
operation_result = operation_classifier.classify(user_input)

# Stage 2: Classify entity type
entity_type_classifier = EntityTypeClassifier(llm_plugin)
entity_type_result = entity_type_classifier.classify(user_input, operation_result.operation_type)

# Stage 3: Extract identifier
identifier_extractor = EntityIdentifierExtractor(llm_plugin)
identifier_result = identifier_extractor.extract(
    user_input, entity_type_result.entity_type, operation_result.operation_type
)

# Stage 4: Extract parameters
parameter_extractor = ParameterExtractor(llm_plugin)
parameter_result = parameter_extractor.extract(
    user_input, operation_result.operation_type, entity_type_result.entity_type
)

# Stage 5: Build OperationContext
context = OperationContext(
    operation=operation_result.operation_type,
    entity_type=entity_type_result.entity_type,
    identifier=identifier_result.identifier,
    parameters=parameter_result.parameters,
    confidence=min(
        operation_result.confidence,
        entity_type_result.confidence,
        identifier_result.confidence,
        parameter_result.confidence
    ),
    raw_input=user_input
)
```

**OR use NLCommandProcessor** (recommended):
```python
from src.nl.nl_command_processor import NLCommandProcessor

processor = NLCommandProcessor(state_manager, llm_plugin)
result = processor.process_command(user_input, project_id=1)
# Handles full pipeline automatically
```

### 2. CommandValidator API Changed

**Old API (v1.3.0)**:
```python
from src.nl.command_validator import CommandValidator

validator = CommandValidator(state_manager)
result = validator.validate(extracted_entities)  # ExtractedEntities object
```

**New API (v1.6.0)**:
```python
from src.nl.command_validator import CommandValidator
from src.nl.types import OperationContext

validator = CommandValidator(state_manager)
result = validator.validate(operation_context)  # OperationContext object
```

**Backward Compatibility (v1.6.0 only)**:
```python
# Legacy API still works in v1.6.0
result = validator.validate_legacy(extracted_entities)

# Will be removed in v1.7.0 - migrate ASAP!
```

### 3. CommandExecutor API Changed

**Old API (v1.3.0)**:
```python
from src.nl.command_executor import CommandExecutor

executor = CommandExecutor(state_manager)
result = executor.execute(validated_command, project_id=1)
```

**New API (v1.6.0)**:
```python
# Same interface, but validated_command structure changed
# Old: validated_command from ExtractedEntities
# New: validated_command from OperationContext

# validated_command structure:
{
    'operation': 'create',  # NEW: operation type
    'entity_type': 'epic',
    'identifier': None,  # NEW: explicit identifier
    'parameters': {  # NEW: operation-specific parameters
        'title': 'User Authentication',
        'description': '...',
        'priority': 'HIGH'
    },
    'confidence': 0.95
}
```

---

## Migration Steps

### Step 1: Identify Usage

**Search for deprecated imports**:
```bash
grep -r "from src.nl.entity_extractor import" src/ tests/
grep -r "from nl.entity_extractor import" src/ tests/
grep -r "ExtractedEntities" src/ tests/
```

**Review results**: Each match requires migration.

### Step 2: Update Imports

**Before**:
```python
from src.nl.entity_extractor import EntityExtractor, ExtractedEntities
```

**After**:
```python
from src.nl.operation_classifier import OperationClassifier
from src.nl.entity_type_classifier import EntityTypeClassifier
from src.nl.entity_identifier_extractor import EntityIdentifierExtractor
from src.nl.parameter_extractor import ParameterExtractor
from src.nl.types import (
    OperationContext, OperationType, EntityType, QueryType,
    OperationResult, EntityTypeResult, IdentifierResult, ParameterResult
)
```

### Step 3: Replace EntityExtractor Calls

**Before (Single Call)**:
```python
extractor = EntityExtractor(llm_plugin)
result = extractor.extract(user_input, intent="COMMAND")
```

**After (Five Calls)**:
```python
# 1. Classify operation
operation_classifier = OperationClassifier(llm_plugin)
operation_result = operation_classifier.classify(user_input)

# 2. Classify entity type
entity_type_classifier = EntityTypeClassifier(llm_plugin)
entity_type_result = entity_type_classifier.classify(user_input, operation_result.operation_type)

# 3. Extract identifier
identifier_extractor = EntityIdentifierExtractor(llm_plugin)
identifier_result = identifier_extractor.extract(
    user_input, entity_type_result.entity_type, operation_result.operation_type
)

# 4. Extract parameters
parameter_extractor = ParameterExtractor(llm_plugin)
parameter_result = parameter_extractor.extract(
    user_input, operation_result.operation_type, entity_type_result.entity_type
)

# 5. Build context
context = OperationContext(
    operation=operation_result.operation_type,
    entity_type=entity_type_result.entity_type,
    identifier=identifier_result.identifier,
    parameters=parameter_result.parameters,
    confidence=min(
        operation_result.confidence,
        entity_type_result.confidence,
        identifier_result.confidence,
        parameter_result.confidence
    ),
    raw_input=user_input
)
```

### Step 4: Update Tests

**Before**:
```python
def test_extract_epic(mock_llm):
    extractor = EntityExtractor(mock_llm)
    result = extractor.extract("Create an epic for auth", "COMMAND")

    assert result.entity_type == "epic"
    assert result.entities[0]["title"] == "auth"
```

**After**:
```python
def test_extract_epic(mock_llm):
    # Test each component separately
    operation_classifier = OperationClassifier(mock_llm)
    entity_type_classifier = EntityTypeClassifier(mock_llm)
    parameter_extractor = ParameterExtractor(mock_llm)

    operation_result = operation_classifier.classify("Create an epic for auth")
    assert operation_result.operation_type == OperationType.CREATE

    entity_type_result = entity_type_classifier.classify(
        "Create an epic for auth", operation_result.operation_type
    )
    assert entity_type_result.entity_type == EntityType.EPIC

    parameter_result = parameter_extractor.extract(
        "Create an epic for auth", operation_result.operation_type, entity_type_result.entity_type
    )
    assert "title" in parameter_result.parameters
```

### Step 5: Verify Migration

**Run tests**:
```bash
source venv/bin/activate
python -m pytest tests/nl/ -v
```

**Check for deprecation warnings**:
```bash
grep -i "deprecated" logs/*.log
```

**Validate accuracy** (if applicable):
```bash
python -m src.cli test-nl-accuracy --commands test_commands.txt
```

---

## New Features in v1.6.0

### 1. UPDATE Operations

**Create → Update transition**:

**Old (v1.3.0)**: UPDATE operations were not well-supported

**New (v1.6.0)**:
```python
# Mark project as INACTIVE
user_input = "Mark the manual tetris test as INACTIVE"

# Pipeline correctly classifies:
# - Operation: UPDATE
# - Entity Type: PROJECT
# - Identifier: "manual tetris test"
# - Parameters: {"status": "INACTIVE"}
```

**Usage**:
```
Mark project 1 as INACTIVE
Set task 5 priority to HIGH
Update epic 3 status to COMPLETED
```

### 2. Hierarchical Queries

**New query types**:

```python
from src.nl.types import QueryType

# HIERARCHICAL / WORKPLAN: Show epic → story → task hierarchy
# NEXT_STEPS: Show next pending tasks
# BACKLOG: Show all pending tasks
# ROADMAP: Show milestones and epics
```

**Usage**:
```
List the workplans for the projects
Show me the backlog for project 1
What's next for the tetris project?
Display the roadmap
```

**Implementation**:
```python
context = OperationContext(
    operation=OperationType.QUERY,
    entity_type=EntityType.PROJECT,
    identifier=None,  # Query all projects
    parameters={"query_type": "HIERARCHICAL"},
    query_type=QueryType.WORKPLAN,
    confidence=0.92,
    raw_input=user_input
)
```

### 3. Question Handling

**New question path**:

**Old (v1.3.0)**: Questions forwarded to Claude Code unconditionally

**New (v1.6.0)**: Intelligent question handling with QuestionHandler

```python
from src.nl.question_handler import QuestionHandler
from src.nl.types import QuestionType, QuestionResponse

handler = QuestionHandler(state_manager, llm_plugin)

# Automatically classifies question type and queries StateManager
response = handler.handle("What's next for project 1?")

# response.question_type = QuestionType.NEXT_STEPS
# response.answer = "Next steps for Project 1: ..."
```

**Question types**:
- `NEXT_STEPS`: "What's next?", "What should I work on?"
- `STATUS`: "What's the status?", "How's progress?"
- `BLOCKERS`: "What's blocking?", "Any issues?"
- `PROGRESS`: "Show progress", "Completion percentage?"
- `GENERAL`: Catch-all for other questions

---

## Configuration Changes

### New Configuration Options (v1.6.0)

```yaml
nl_commands:
  enabled: true

  # NEW: Individual component confidence thresholds
  component_thresholds:
    operation_classifier: 0.7
    entity_type_classifier: 0.7
    entity_identifier_extractor: 0.7
    parameter_extractor: 0.7
    question_handler: 0.7

  # NEW: Query type support
  hierarchical_queries:
    enabled: true
    max_depth: 5  # Max nesting level for hierarchies

  # NEW: Question handling
  question_handling:
    enabled: true
    fallback_to_claude: true  # Fallback to Claude Code if no match

  # DEPRECATED: Legacy pipeline (v1.6.0 only, removed in v1.7.0)
  use_legacy_pipeline: false  # Set to true for rollback
```

---

## Rollback Plan

### If You Need to Rollback

**Scenario**: ADR-016 causes issues, need to revert to v1.3.0 behavior

**Option 1: Configuration Rollback** (v1.6.0 only)

```yaml
nl_commands:
  use_legacy_pipeline: true  # Enable backward compatibility
```

**Option 2: Version Downgrade**

```bash
git checkout v1.3.0
pip install -r requirements.txt
python -m src.cli interactive
```

**Option 3: Disable NL Commands**

```yaml
nl_commands:
  enabled: false  # Disable NL entirely, use slash commands
```

---

## Testing Your Integration

### Unit Tests

**Test individual components**:

```python
import pytest
from src.nl.operation_classifier import OperationClassifier
from src.nl.types import OperationType

def test_operation_classifier(mock_llm):
    classifier = OperationClassifier(mock_llm, confidence_threshold=0.7)
    result = classifier.classify("Create an epic for auth")

    assert result.operation_type == OperationType.CREATE
    assert result.confidence >= 0.7
```

### Integration Tests

**Test full pipeline**:

```python
from src.nl.nl_command_processor import NLCommandProcessor

def test_full_pipeline(state_manager, mock_llm):
    processor = NLCommandProcessor(state_manager, mock_llm)
    result = processor.process_command("Create an epic for auth", project_id=1)

    assert result.success is True
    assert len(result.created_ids) == 1
```

### Manual Testing

**Test real-world scenarios**:

```bash
python -m src.cli interactive

# Test CREATE
orchestrator> Create an epic for user authentication
✓ Created Epic #5: User Authentication

# Test UPDATE
orchestrator> Mark epic 5 as INACTIVE
✓ Updated Epic #5: status: INACTIVE

# Test QUERY
orchestrator> List the workplans for the projects
✓ Showing hierarchical workplan: ...

# Test QUESTION
orchestrator> What's next for project 1?
✓ Next steps for Project 1: ...
```

---

## Troubleshooting

### Issue: Tests Failing After Migration

**Symptom**: `AttributeError: 'ExtractedEntities' object has no attribute 'operation'`

**Solution**: Update tests to use `OperationContext`:

```python
# Before
assert extracted.entity_type == "epic"

# After
assert context.operation == OperationType.CREATE
assert context.entity_type == EntityType.EPIC
```

### Issue: Validation Errors

**Symptom**: `ValidationError: UPDATE operation requires an identifier`

**Solution**: Ensure OperationContext includes identifier for UPDATE/DELETE:

```python
context = OperationContext(
    operation=OperationType.UPDATE,
    entity_type=EntityType.PROJECT,
    identifier="manual tetris test",  # REQUIRED for UPDATE!
    parameters={"status": "INACTIVE"}
)
```

### Issue: Low Accuracy

**Symptom**: Commands frequently trigger clarification requests

**Solution**: Check LLM provider performance:

```bash
# Test LLM latency
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5-coder:32b", "prompt": "Test"}'

# Should respond in <200ms
```

### Issue: Performance Regression

**Symptom**: NL commands take >3 seconds (vs <1s in v1.3.0)

**Solution**:
1. **Check LLM provider**: Ensure Ollama/Qwen is running locally (not remote)
2. **Reduce context**: Lower `max_context_turns` in config
3. **Use rollback**: Enable `use_legacy_pipeline: true` temporarily

---

## FAQ

### Q: When will EntityExtractor be removed?

**A**: EntityExtractor is deprecated in v1.6.0 and will be removed in v1.7.0 (estimated: Q1 2026). Migrate by v1.7.0 release.

### Q: Can I use both old and new APIs?

**A**: Yes, in v1.6.0 only. Use `validate_legacy()` for backward compatibility. This will be removed in v1.7.0.

### Q: Will migration break my production deployment?

**A**: No, if you only use high-level APIs (NLCommandProcessor, interactive CLI). If you use EntityExtractor directly, migrate before v1.7.0.

### Q: How do I know if migration was successful?

**A**: Run full test suite + manual testing:

```bash
python -m pytest tests/nl/ -v --cov=src/nl
python -m src.cli interactive  # Manual testing
```

All tests should pass, and NL commands should work as expected.

### Q: What if I find bugs after migration?

**A**: Report issues at [GitHub Issues](https://github.com/Omar-Unpossible/claude_code_orchestrator/issues) with:
- Error messages
- Input command that failed
- Expected vs. actual behavior
- Logs from `logs/nl_commands.log`

---

## Migration Checklist

Use this checklist to track your migration progress:

- [ ] **Step 1**: Identify all usages of EntityExtractor in codebase
- [ ] **Step 2**: Update imports to use new classifiers
- [ ] **Step 3**: Replace EntityExtractor calls with 5-stage pipeline
- [ ] **Step 4**: Update tests to use OperationContext API
- [ ] **Step 5**: Update CommandValidator.validate() calls (remove validate_legacy())
- [ ] **Step 6**: Run full test suite and verify all pass
- [ ] **Step 7**: Manual testing of CREATE, UPDATE, DELETE, QUERY, QUESTION
- [ ] **Step 8**: Performance testing (latency <1.5s, accuracy >95%)
- [ ] **Step 9**: Update documentation and internal guides
- [ ] **Step 10**: Deploy to staging environment
- [ ] **Step 11**: Monitor logs for deprecation warnings
- [ ] **Step 12**: Deploy to production

---

## Support

- **Technical Questions**: See [docs/guides/NL_COMMAND_GUIDE.md](NL_COMMAND_GUIDE.md)
- **Architecture Details**: See [docs/decisions/ADR-016-decompose-nl-entity-extraction.md](../decisions/ADR-016-decompose-nl-entity-extraction.md)
- **Test Examples**: See `tests/nl/test_integration_full_pipeline.py`
- **Issues**: Report at [GitHub Issues](https://github.com/Omar-Unpossible/claude_code_orchestrator/issues)

---

**Migration Guide Version**: 1.0
**Last Updated**: November 11, 2025
**Target Version**: v1.6.0 (ADR-016)
**Deprecation Timeline**: EntityExtractor removed in v1.7.0 (Q1 2026)
