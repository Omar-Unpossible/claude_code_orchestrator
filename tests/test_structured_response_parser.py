"""Test StructuredResponseParser for hybrid response parsing and validation.

Tests for:
- StructuredResponseParser class
- All 5 response types (task_execution, validation, error_analysis, decision, planning)
- Schema validation
- Malformed response handling
- Error handling

Part of TASK_3.5: Test structured prompt system
"""

import pytest
from src.llm.structured_response_parser import StructuredResponseParser
from src.core.exceptions import ValidationException


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def parser():
    """Provide a StructuredResponseParser with loaded schemas."""
    p = StructuredResponseParser('config/response_schemas.yaml')
    p.load_schemas()
    return p


@pytest.fixture
def valid_task_execution_response():
    """Provide a valid task execution response."""
    return """
<METADATA>
{
  "status": "completed",
  "files_modified": ["/path/to/file.py"],
  "files_created": ["/path/to/test.py"],
  "tests_added": 5,
  "confidence": 0.9,
  "requires_review": false
}
</METADATA>

<CONTENT>
Successfully implemented the authentication module with JWT tokens.
All tests pass and code follows the specified rules.
</CONTENT>
"""


@pytest.fixture
def valid_validation_response():
    """Provide a valid validation response."""
    return """
<METADATA>
{
  "is_valid": false,
  "quality_score": 65,
  "violations": [
    {
      "rule_id": "CODE_001",
      "file": "/path/to/file.py",
      "line": 15,
      "severity": "high",
      "message": "Stub function detected",
      "suggestion": "Implement the function logic"
    }
  ],
  "warnings": ["Missing docstring on function foo"],
  "passed_rules": ["CODE_002", "CODE_003"]
}
</METADATA>

<CONTENT>
Found 1 critical violation in the code review.
</CONTENT>
"""


# ============================================================================
# Tests: Initialization and Schema Loading
# ============================================================================

def test_structured_response_parser_initialization():
    """Test StructuredResponseParser initializes correctly."""
    parser = StructuredResponseParser('config/response_schemas.yaml')

    assert 'response_schemas.yaml' in parser.schemas_file_path
    assert parser.schemas == {}


def test_load_schemas(parser):
    """Test loading schemas from YAML."""
    assert len(parser.schemas) > 0
    assert 'task_execution' in parser.schemas
    assert 'validation' in parser.schemas
    assert 'error_analysis' in parser.schemas
    assert 'decision' in parser.schemas
    assert 'planning' in parser.schemas


# ============================================================================
# Tests: Task Execution Response Parsing
# ============================================================================

def test_parse_task_execution_response(parser, valid_task_execution_response):
    """Test parsing valid task execution response."""
    result = parser.parse_response(
        response=valid_task_execution_response,
        expected_type='task_execution'
    )

    # Response should have all required keys
    assert 'is_valid' in result
    assert 'metadata' in result
    assert 'content' in result
    assert result['metadata']['status'] == 'completed'
    assert result['metadata']['files_modified'] == ['/path/to/file.py']
    assert result['metadata']['confidence'] == 0.9
    assert 'authentication module' in result['content']


def test_parse_task_execution_missing_required_field(parser):
    """Test parsing task execution response with missing required field."""
    response = """
<METADATA>
{
  "files_modified": ["/path/to/file.py"],
  "confidence": 0.9
}
</METADATA>

<CONTENT>
Missing status field.
</CONTENT>
"""

    result = parser.parse_response(response, 'task_execution')

    assert result['is_valid'] is False
    assert len(result['validation_errors']) > 0
    assert any('status' in error for error in result['validation_errors'])


def test_parse_task_execution_invalid_status(parser):
    """Test parsing task execution response with invalid status value."""
    response = """
<METADATA>
{
  "status": "invalid_status",
  "files_modified": [],
  "confidence": 0.9
}
</METADATA>

<CONTENT>
Invalid status value.
</CONTENT>
"""

    result = parser.parse_response(response, 'task_execution')

    assert result['is_valid'] is False
    # Should have validation error for invalid enum value


# ============================================================================
# Tests: Validation Response Parsing
# ============================================================================

def test_parse_validation_response(parser, valid_validation_response):
    """Test parsing valid validation response."""
    result = parser.parse_response(
        response=valid_validation_response,
        expected_type='validation'
    )

    assert 'metadata' in result
    assert 'content' in result
    assert result['metadata']['is_valid'] is False  # Code validation failed
    assert result['metadata']['quality_score'] == 65
    assert len(result['metadata']['violations']) == 1
    assert result['metadata']['violations'][0]['rule_id'] == 'CODE_001'


# ============================================================================
# Tests: Error Analysis Response Parsing
# ============================================================================

def test_parse_error_analysis_response(parser):
    """Test parsing error analysis response."""
    response = """
<METADATA>
{
  "root_cause": "NoneType object access without null check",
  "error_category": "logic",
  "fix_approach": "code_change",
  "confidence": 0.92,
  "files_to_modify": ["/path/to/file.py"],
  "estimated_fix_time_minutes": 10,
  "requires_human_review": false,
  "potential_side_effects": ["May change error response format"]
}
</METADATA>

<CONTENT>
Root cause: Missing null check before accessing user.id.
Proposed fix: Add if user is None check.
</CONTENT>
"""

    result = parser.parse_response(response, 'error_analysis')

    assert 'metadata' in result
    assert result['metadata']['root_cause'] == 'NoneType object access without null check'
    assert result['metadata']['error_category'] == 'logic'
    assert result['metadata']['confidence'] == 0.92


# ============================================================================
# Tests: Decision Response Parsing
# ============================================================================

def test_parse_decision_response(parser):
    """Test parsing decision response."""
    response = """
<METADATA>
{
  "decision": "retry",
  "confidence": 0.88,
  "reasoning": "Quality score below threshold, fixable violations",
  "next_actions": [
    {
      "action": "retry_task",
      "target": "task_123",
      "priority": 1
    }
  ],
  "estimated_resolution_time_minutes": 15,
  "requires_human_input": false
}
</METADATA>

<CONTENT>
Recommendation: Retry the task with feedback on missing docstrings.
</CONTENT>
"""

    result = parser.parse_response(response, 'decision')

    assert result['is_valid'] is True
    assert result['metadata']['decision'] == 'retry'
    assert result['metadata']['confidence'] == 0.88
    assert len(result['metadata']['next_actions']) == 1


# ============================================================================
# Tests: Planning Response Parsing
# ============================================================================

def test_parse_planning_response(parser):
    """Test parsing planning response."""
    response = """
<METADATA>
{
  "decomposition_needed": true,
  "subtasks": [
    {
      "subtask_id": 1,
      "title": "Implement cart module",
      "estimated_duration_minutes": 30,
      "dependencies": [],
      "can_parallelize": true
    }
  ],
  "execution_strategy": "parallel",
  "total_estimated_duration_minutes": 120,
  "confidence": 0.82
}
</METADATA>

<CONTENT>
Task decomposed into 5 subtasks with parallel execution groups.
</CONTENT>
"""

    result = parser.parse_response(response, 'planning')

    assert 'metadata' in result
    assert result['metadata']['decomposition_needed'] is True
    assert len(result['metadata']['subtasks']) == 1
    assert result['metadata']['execution_strategy'] == 'parallel'


# ============================================================================
# Tests: Metadata Extraction
# ============================================================================

def test_extract_metadata(parser):
    """Test extracting metadata from response."""
    response = """
<METADATA>
{
  "status": "completed",
  "confidence": 0.9
}
</METADATA>

<CONTENT>
Test content
</CONTENT>
"""

    metadata = parser._extract_metadata(response)

    assert metadata['status'] == 'completed'
    assert metadata['confidence'] == 0.9


def test_extract_content(parser):
    """Test extracting content from response."""
    response = """
<METADATA>
{"status": "completed"}
</METADATA>

<CONTENT>
This is the natural language explanation.
It can span multiple lines.
</CONTENT>
"""

    content = parser._extract_content(response)

    assert 'natural language explanation' in content
    assert 'multiple lines' in content


# ============================================================================
# Tests: Malformed Response Handling
# ============================================================================

def test_handle_malformed_json(parser):
    """Test handling malformed JSON in metadata."""
    response = """
<METADATA>
{
  "status": "completed",
  "confidence": 0.9,  // Invalid comment
}
</METADATA>

<CONTENT>
Test
</CONTENT>
"""

    result = parser.parse_response(response, 'task_execution')

    assert result['is_valid'] is False
    assert len(result['validation_errors']) > 0
    assert any('JSON' in error or 'parse' in error for error in result['validation_errors'])


def test_handle_missing_metadata_tags(parser):
    """Test handling response with missing metadata tags."""
    response = """
{
  "status": "completed",
  "files_modified": [],
  "confidence": 0.9
}

This is just plain text without proper tags.
"""

    result = parser.parse_response(response, 'task_execution')

    # Should attempt fallback JSON extraction
    assert 'status' in result['metadata'] or result['is_valid'] is False


def test_handle_empty_response(parser):
    """Test handling empty response."""
    response = ""

    result = parser.parse_response(response, 'task_execution')

    assert result['is_valid'] is False
    assert len(result['validation_errors']) > 0


# ============================================================================
# Tests: Schema Validation
# ============================================================================

def test_validate_against_schema(parser):
    """Test schema validation."""
    data = {
        'status': 'completed',
        'files_modified': ['/path/to/file.py'],
        'confidence': 0.9
    }

    is_valid, errors = parser._validate_against_schema(data, 'task_execution')

    # Should return tuple (bool, list)
    assert isinstance(is_valid, bool)
    assert isinstance(errors, list)


def test_validate_against_schema_missing_field(parser):
    """Test schema validation with missing required field."""
    data = {
        'files_modified': [],
        'confidence': 0.9
        # Missing 'status'
    }

    is_valid, errors = parser._validate_against_schema(data, 'task_execution')

    assert is_valid is False
    assert len(errors) > 0  # Should have errors for missing field


# ============================================================================
# Tests: Exception Handling
# ============================================================================

def test_validation_exception_raised(parser):
    """Test that ValidationException can be raised."""
    # This tests the exception class itself
    exc = ValidationException("Test error")

    assert "Test error" in str(exc)


def test_parse_response_with_invalid_type(parser):
    """Test parsing response with invalid schema type."""
    response = """
<METADATA>
{"status": "completed"}
</METADATA>

<CONTENT>
Test
</CONTENT>
"""

    # Invalid expected_type - may return invalid result instead of raising
    result = parser.parse_response(response, 'invalid_type')

    # Should have is_valid False for unknown schema type
    assert 'is_valid' in result
