"""Tests for JSON extraction utilities."""

import pytest
from src.utils.json_extractor import extract_json, validate_json_structure, ensure_json_keys


class TestExtractJson:
    """Test JSON extraction from LLM responses."""

    def test_extract_plain_json(self):
        """Test extraction of plain JSON."""
        response = '{"key": "value", "number": 42}'
        result = extract_json(response)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_with_preamble(self):
        """Test extraction when LLM adds preamble."""
        response = 'Sure, here is the JSON:\n{"key": "value"}'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_extract_json_with_postamble(self):
        """Test extraction when LLM adds explanation after."""
        response = '{"key": "value"}\nI hope this helps!'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_extract_json_with_both(self):
        """Test extraction with both preamble and postamble."""
        response = 'Here you go:\n{"key": "value"}\nLet me know if you need more.'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_extract_json_from_markdown(self):
        """Test extraction from markdown code block."""
        response = '```json\n{"key": "value"}\n```'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_extract_json_from_markdown_no_language(self):
        """Test extraction from markdown without json language tag."""
        response = '```\n{"key": "value"}\n```'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_extract_nested_json(self):
        """Test extraction of nested JSON."""
        response = '{"outer": {"inner": "value"}}'
        result = extract_json(response)
        assert result == {"outer": {"inner": "value"}}

    def test_extract_json_with_arrays(self):
        """Test extraction with array values."""
        response = '{"items": ["a", "b", "c"]}'
        result = extract_json(response)
        assert result == {"items": ["a", "b", "c"]}

    def test_extract_complex_nested(self):
        """Test extraction of complex nested structure."""
        response = '''
        {
            "is_valid": true,
            "quality_score": 0.85,
            "issues": ["Issue 1", "Issue 2"],
            "details": {
                "syntax": "good",
                "testing": "needs work"
            }
        }
        '''
        result = extract_json(response)
        assert result is not None
        assert result["is_valid"] is True
        assert result["quality_score"] == 0.85
        assert len(result["issues"]) == 2
        assert "details" in result

    def test_extract_with_escaped_quotes(self):
        """Test extraction with escaped quotes in values."""
        response = '{"message": "He said \\"hello\\""}'
        result = extract_json(response)
        assert result == {"message": 'He said "hello"'}

    def test_extract_with_numbers(self):
        """Test extraction with various number types."""
        response = '{"int": 42, "float": 3.14, "negative": -10}'
        result = extract_json(response)
        assert result == {"int": 42, "float": 3.14, "negative": -10}

    def test_extract_with_booleans(self):
        """Test extraction with boolean values."""
        response = '{"true_val": true, "false_val": false}'
        result = extract_json(response)
        assert result == {"true_val": True, "false_val": False}

    def test_extract_with_null(self):
        """Test extraction with null values."""
        response = '{"nullable": null}'
        result = extract_json(response)
        assert result == {"nullable": None}

    def test_extract_returns_none_on_invalid(self):
        """Test that extraction returns None for invalid JSON."""
        response = 'This is not JSON at all'
        result = extract_json(response)
        assert result is None

    def test_extract_handles_empty_string(self):
        """Test handling of empty response."""
        result = extract_json('')
        assert result is None

    def test_extract_handles_whitespace_only(self):
        """Test handling of whitespace-only response."""
        result = extract_json('   \n\t  ')
        assert result is None

    def test_extract_json_with_multiline_strings(self):
        """Test extraction with multiline string values."""
        response = '{"description": "Line 1\\nLine 2\\nLine 3"}'
        result = extract_json(response)
        assert result == {"description": "Line 1\nLine 2\nLine 3"}


class TestValidateJsonStructure:
    """Test JSON structure validation."""

    def test_validate_all_required_present(self):
        """Test validation passes when all required keys present."""
        data = {"a": 1, "b": 2, "c": 3}
        is_valid, error = validate_json_structure(data, ["a", "b"])
        assert is_valid is True
        assert error is None

    def test_validate_missing_required(self):
        """Test validation fails when required keys missing."""
        data = {"a": 1}
        is_valid, error = validate_json_structure(data, ["a", "b", "c"])
        assert is_valid is False
        assert "b" in error and "c" in error

    def test_validate_missing_single_key(self):
        """Test validation fails with single missing key."""
        data = {"a": 1, "c": 3}
        is_valid, error = validate_json_structure(data, ["a", "b", "c"])
        assert is_valid is False
        assert "b" in error
        assert "a" not in error  # a is present
        assert "c" not in error  # c is present

    def test_validate_empty_required_list(self):
        """Test validation passes with no required keys."""
        data = {"a": 1}
        is_valid, error = validate_json_structure(data, [])
        assert is_valid is True
        assert error is None

    def test_validate_not_dict(self):
        """Test validation fails for non-dict data."""
        is_valid, error = validate_json_structure([], ["key"])
        assert is_valid is False
        assert "not a JSON object" in error

    def test_validate_not_dict_string(self):
        """Test validation fails for string data."""
        is_valid, error = validate_json_structure("not a dict", ["key"])
        assert is_valid is False
        assert "not a JSON object" in error

    def test_validate_with_optional_keys(self):
        """Test validation with optional keys (not checked)."""
        data = {"required": 1}
        is_valid, error = validate_json_structure(
            data,
            required_keys=["required"],
            optional_keys=["optional"]
        )
        assert is_valid is True
        assert error is None


class TestEnsureJsonKeys:
    """Test ensuring JSON has required keys with defaults."""

    def test_ensure_all_keys_present(self):
        """Test when all keys already present."""
        data = {"a": 1, "b": 2}
        required = {"a": 0, "b": 0}
        result = ensure_json_keys(data, required)
        assert result == {"a": 1, "b": 2}

    def test_ensure_adds_missing_keys(self):
        """Test that missing keys are added with defaults."""
        data = {"a": 1}
        required = {"a": 0, "b": "default", "c": []}
        result = ensure_json_keys(data, required)
        assert result == {"a": 1, "b": "default", "c": []}

    def test_ensure_preserves_existing_values(self):
        """Test that existing values are not overwritten."""
        data = {"a": 100}
        required = {"a": 0}
        result = ensure_json_keys(data, required)
        assert result["a"] == 100

    def test_ensure_with_empty_required(self):
        """Test with no required keys."""
        data = {"a": 1}
        required = {}
        result = ensure_json_keys(data, required)
        assert result == {"a": 1}

    def test_ensure_with_not_dict(self):
        """Test handling of non-dict data."""
        data = "not a dict"
        required = {"a": 0, "b": 1}
        result = ensure_json_keys(data, required)
        # Should return defaults when data is not dict
        assert result == {"a": 0, "b": 1}

    def test_ensure_with_none(self):
        """Test handling of None data."""
        data = None
        required = {"a": 0}
        result = ensure_json_keys(data, required)
        assert result == {"a": 0}

    def test_ensure_doesnt_modify_original(self):
        """Test that original data is not modified."""
        data = {"a": 1}
        required = {"a": 0, "b": 2}
        result = ensure_json_keys(data, required)
        # Original should not have 'b'
        assert "b" not in data
        # Result should have 'b'
        assert "b" in result


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_validation_response_typical(self):
        """Test typical validation response from LLM."""
        response = '''
        {
            "is_valid": true,
            "quality_score": 0.85,
            "issues": [],
            "suggestions": ["Add more tests"]
        }
        '''
        result = extract_json(response)
        assert result is not None

        is_valid, error = validate_json_structure(
            result,
            required_keys=["is_valid", "quality_score", "issues", "suggestions"]
        )
        assert is_valid is True

    def test_validation_response_with_preamble(self):
        """Test validation response with LLM preamble."""
        response = '''
        Based on my analysis, here is the validation result:

        {
            "is_valid": false,
            "quality_score": 0.45,
            "issues": ["Missing error handling", "No tests"],
            "suggestions": ["Add try-catch blocks", "Write unit tests"]
        }

        I hope this helps!
        '''
        result = extract_json(response)
        assert result is not None
        assert result["is_valid"] is False
        assert len(result["issues"]) == 2

    def test_validation_response_markdown(self):
        """Test validation response in markdown code block."""
        response = '''
        Here is the validation:

        ```json
        {
            "is_valid": true,
            "quality_score": 0.92,
            "issues": [],
            "suggestions": []
        }
        ```
        '''
        result = extract_json(response)
        assert result is not None
        assert result["quality_score"] == 0.92

    def test_malformed_recovery(self):
        """Test recovery from malformed response."""
        response = 'The result is: {"is_valid": true, but I think...'
        result = extract_json(response)
        # Should extract partial valid JSON
        if result is not None:
            # If it extracted something, verify it's the valid part
            assert "is_valid" in result

    def test_ensure_defaults_for_incomplete_llm(self):
        """Test ensuring defaults when LLM returns incomplete JSON."""
        response = '{"is_valid": true}'  # Missing other required keys
        result = extract_json(response)
        assert result is not None

        # Ensure all required keys present
        complete = ensure_json_keys(result, {
            "is_valid": False,
            "quality_score": 0.0,
            "issues": [],
            "suggestions": []
        })

        assert "quality_score" in complete
        assert "issues" in complete
        assert complete["is_valid"] is True  # Original value preserved
