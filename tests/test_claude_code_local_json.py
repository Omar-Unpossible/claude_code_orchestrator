"""Tests for ClaudeCodeLocalAgent JSON parsing (Phase 1, Task 1.4).

Tests the JSON output format parsing, metadata extraction, and error handling
for the headless Claude Code agent.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

import pytest

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.plugins.exceptions import AgentException


class TestJSONParsing:
    """Test JSON response parsing functionality."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create and initialize agent for testing."""
        agent = ClaudeCodeLocalAgent()
        agent.initialize({
            'workspace_path': str(tmp_path),
            'response_timeout': 120,
            'use_session_persistence': False,
            'bypass_permissions': True
        })
        return agent

    @pytest.fixture
    def success_json_response(self):
        """Sample successful JSON response from Claude Code."""
        return {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "duration_ms": 14301,
            "duration_api_ms": 27618,
            "num_turns": 2,
            "result": "I successfully completed the task. Here are the changes...",
            "session_id": "550e8400-e29b-41d4-a716-446655440001",
            "total_cost_usd": 0.013645,
            "usage": {
                "input_tokens": 9,
                "cache_creation_input_tokens": 12871,
                "cache_read_input_tokens": 36391,
                "output_tokens": 510,
                "server_tool_use": {
                    "web_search_requests": 0,
                    "web_fetch_requests": 0
                },
                "service_tier": "standard",
                "cache_creation": {
                    "ephemeral_1h_input_tokens": 0,
                    "ephemeral_5m_input_tokens": 12871
                }
            },
            "modelUsage": {
                "claude-sonnet-4-5-20250929": {
                    "inputTokens": 0,
                    "outputTokens": 774,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                    "webSearchRequests": 0,
                    "costUSD": 0.01161,
                    "contextWindow": 200000
                },
                "claude-haiku-4-5-20251001": {
                    "inputTokens": 0,
                    "outputTokens": 407,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                    "webSearchRequests": 0,
                    "costUSD": 0.00203,
                    "contextWindow": 200000
                }
            },
            "permission_denials": [],
            "uuid": "3eb1e1b4-106d-48ef-8127-1a1bcc6b9c3e"
        }

    @pytest.fixture
    def error_max_turns_response(self):
        """Sample error_max_turns JSON response from Claude Code."""
        return {
            "type": "result",
            "subtype": "error_max_turns",
            "duration_ms": 207832,
            "duration_api_ms": 222532,
            "is_error": False,  # NOTE: Not marked as error!
            "num_turns": 2,
            "result": "I ran out of turns. Here's what I completed so far...",
            "session_id": "550e8400-e29b-41d4-a716-446655440002",
            "total_cost_usd": 0.16741,
            "usage": {
                "input_tokens": 3,
                "cache_creation_input_tokens": 8999,
                "cache_read_input_tokens": 14981,
                "output_tokens": 456
            },
            "modelUsage": {
                "claude-haiku-4-5-20251001": {
                    "inputTokens": 0,
                    "outputTokens": 353,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                    "webSearchRequests": 0,
                    "costUSD": 0.001765,
                    "contextWindow": 200000
                },
                "claude-sonnet-4-5-20250929": {
                    "inputTokens": 0,
                    "outputTokens": 11043,
                    "cacheReadInputTokens": 0,
                    "cacheCreationInputTokens": 0,
                    "webSearchRequests": 0,
                    "costUSD": 0.165645,
                    "contextWindow": 200000
                }
            },
            "permission_denials": [
                {
                    "tool_name": "Bash",
                    "tool_use_id": "toolu_01W8cSRZ2WmrrQxV5j4suQ3q",
                    "tool_input": {
                        "command": "tree -L 3 /home/omarwsl/projects/...",
                        "description": "Show directory tree structure"
                    }
                }
            ],
            "uuid": "eeb6ebee-680d-45cf-91a2-b47836364924",
            "errors": []
        }

    def test_send_prompt_uses_json_output_format(self, agent):
        """Test that send_prompt adds --output-format json flag."""
        with patch.object(agent, '_run_claude') as mock_run:
            # Mock successful JSON response
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"type":"result","subtype":"success","result":"test"}'
            mock_run.return_value = mock_result

            agent.send_prompt("test prompt")

            # Verify _run_claude was called with JSON format flag
            args = mock_run.call_args[0][0]
            assert '--output-format' in args
            assert 'json' in args

    def test_send_prompt_parses_success_response(self, agent, success_json_response):
        """Test successful JSON response parsing."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(success_json_response)
            mock_run.return_value = mock_result

            response = agent.send_prompt("test prompt")

            # Should return just the result text
            assert response == "I successfully completed the task. Here are the changes..."

            # Metadata should be stored
            assert agent.last_metadata is not None

    def test_send_prompt_parses_error_max_turns(self, agent, error_max_turns_response):
        """Test error_max_turns JSON response parsing."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(error_max_turns_response)
            mock_run.return_value = mock_result

            response = agent.send_prompt("test prompt")

            # Should still return result text
            assert "ran out of turns" in response.lower()

            # Metadata should indicate error_max_turns
            assert agent.last_metadata is not None
            assert agent.last_metadata['error_subtype'] == 'error_max_turns'

    def test_extract_metadata_token_usage(self, agent, success_json_response):
        """Test metadata extraction - token usage fields."""
        metadata = agent._extract_metadata(success_json_response)

        assert metadata['input_tokens'] == 9
        assert metadata['cache_creation_tokens'] == 12871
        assert metadata['cache_read_tokens'] == 36391
        assert metadata['output_tokens'] == 510
        # Total = 9 + 12871 + 36391 + 510 = 49781
        assert metadata['total_tokens'] == 49781

    def test_extract_metadata_cache_hit_rate(self, agent, success_json_response):
        """Test metadata extraction - cache hit rate calculation."""
        metadata = agent._extract_metadata(success_json_response)

        # cache_hit_rate = cache_read / (input + cache_creation + cache_read)
        # = 36391 / (9 + 12871 + 36391) = 36391 / 49271 = 0.738...
        assert metadata['cache_hit_rate'] > 0.73
        assert metadata['cache_hit_rate'] < 0.74

    def test_extract_metadata_performance_metrics(self, agent, success_json_response):
        """Test metadata extraction - performance metrics."""
        metadata = agent._extract_metadata(success_json_response)

        assert metadata['duration_ms'] == 14301
        assert metadata['duration_api_ms'] == 27618
        assert metadata['num_turns'] == 2

    def test_extract_metadata_session_info(self, agent, success_json_response):
        """Test metadata extraction - session info."""
        metadata = agent._extract_metadata(success_json_response)

        assert metadata['session_id'] == "550e8400-e29b-41d4-a716-446655440001"
        assert metadata['uuid'] == "3eb1e1b4-106d-48ef-8127-1a1bcc6b9c3e"

    def test_extract_metadata_cost_tracking(self, agent, success_json_response):
        """Test metadata extraction - cost tracking."""
        metadata = agent._extract_metadata(success_json_response)

        assert metadata['cost_usd'] == 0.013645

    def test_extract_metadata_response_status(self, agent, success_json_response):
        """Test metadata extraction - response status fields."""
        metadata = agent._extract_metadata(success_json_response)

        assert metadata['type'] == 'result'
        assert metadata['subtype'] == 'success'
        assert metadata['is_error'] is False
        assert metadata['error_subtype'] is None  # None for success

    def test_extract_metadata_error_subtype(self, agent, error_max_turns_response):
        """Test metadata extraction - error_subtype for non-success."""
        metadata = agent._extract_metadata(error_max_turns_response)

        assert metadata['subtype'] == 'error_max_turns'
        assert metadata['error_subtype'] == 'error_max_turns'
        assert len(metadata['permission_denials']) == 1

    def test_extract_metadata_model_usage(self, agent, success_json_response):
        """Test metadata extraction - per-model usage breakdown."""
        metadata = agent._extract_metadata(success_json_response)

        assert 'model_usage' in metadata
        assert 'claude-sonnet-4-5-20250929' in metadata['model_usage']
        assert 'claude-haiku-4-5-20251001' in metadata['model_usage']

    def test_get_last_metadata_returns_none_initially(self, agent):
        """Test get_last_metadata() returns None before any send_prompt."""
        assert agent.get_last_metadata() is None

    def test_get_last_metadata_after_send_prompt(self, agent, success_json_response):
        """Test get_last_metadata() returns metadata after send_prompt."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(success_json_response)
            mock_run.return_value = mock_result

            agent.send_prompt("test")

            metadata = agent.get_last_metadata()
            assert metadata is not None
            assert metadata['total_tokens'] == 49781

    def test_json_parse_failure_fallback(self, agent):
        """Test graceful fallback when JSON parsing fails."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Not valid JSON response"
            mock_run.return_value = mock_result

            # Should not raise, should return raw text
            response = agent.send_prompt("test")

            assert response == "Not valid JSON response"
            assert agent.last_metadata is None

    def test_json_missing_result_field(self, agent):
        """Test handling of JSON with missing 'result' field."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            # JSON without 'result' field
            mock_result.stdout = '{"type":"result","subtype":"success"}'
            mock_run.return_value = mock_result

            response = agent.send_prompt("test")

            # Should return empty string (default for missing result)
            assert response == ""
            # Metadata should still be extracted
            assert agent.last_metadata is not None

    def test_json_missing_usage_field(self, agent):
        """Test handling of JSON with missing 'usage' field."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            # JSON without 'usage' field
            mock_result.stdout = '{"type":"result","subtype":"success","result":"ok"}'
            mock_run.return_value = mock_result

            response = agent.send_prompt("test")

            assert response == "ok"
            metadata = agent.get_last_metadata()

            # Should have zero token counts
            assert metadata['total_tokens'] == 0
            assert metadata['input_tokens'] == 0

    def test_cache_hit_rate_zero_denominator(self, agent):
        """Test cache hit rate calculation with zero denominator."""
        json_response = {
            "type": "result",
            "subtype": "success",
            "result": "test",
            "usage": {
                "input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 0
            }
        }

        metadata = agent._extract_metadata(json_response)

        # Should not divide by zero, should be 0.0
        assert metadata['cache_hit_rate'] == 0.0

    def test_session_id_in_command_args(self, agent):
        """Test that session ID is included in command arguments."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"type":"result","subtype":"success","result":"test"}'
            mock_run.return_value = mock_result

            agent.send_prompt("test")

            args = mock_run.call_args[0][0]
            assert '--session-id' in args
            # Should have a UUID after --session-id
            session_id_index = args.index('--session-id')
            session_id = args[session_id_index + 1]
            assert len(session_id) == 36  # UUID format: 8-4-4-4-12

    def test_dangerous_mode_flag_included(self, agent):
        """Test that --dangerously-skip-permissions flag is included."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"type":"result","subtype":"success","result":"test"}'
            mock_run.return_value = mock_result

            agent.send_prompt("test")

            args = mock_run.call_args[0][0]
            assert '--dangerously-skip-permissions' in args

    def test_dangerous_mode_can_be_disabled(self, tmp_path):
        """Test that dangerous mode can be disabled via config."""
        agent = ClaudeCodeLocalAgent()
        agent.initialize({
            'workspace_path': str(tmp_path),
            'bypass_permissions': False  # Disable dangerous mode
        })

        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"type":"result","subtype":"success","result":"test"}'
            mock_run.return_value = mock_result

            agent.send_prompt("test")

            args = mock_run.call_args[0][0]
            assert '--dangerously-skip-permissions' not in args

    def test_metadata_persistence_across_calls(self, agent, success_json_response):
        """Test that last_metadata is updated with each call."""
        with patch.object(agent, '_run_claude') as mock_run:
            # First call
            mock_result1 = MagicMock()
            mock_result1.returncode = 0
            response1 = success_json_response.copy()
            response1['usage']['output_tokens'] = 100
            mock_result1.stdout = json.dumps(response1)

            # Second call
            mock_result2 = MagicMock()
            mock_result2.returncode = 0
            response2 = success_json_response.copy()
            response2['usage']['output_tokens'] = 200
            mock_result2.stdout = json.dumps(response2)

            mock_run.side_effect = [mock_result1, mock_result2]

            # First call
            agent.send_prompt("test1")
            metadata1 = agent.get_last_metadata()
            assert metadata1['output_tokens'] == 100

            # Second call
            agent.send_prompt("test2")
            metadata2 = agent.get_last_metadata()
            assert metadata2['output_tokens'] == 200

    def test_logging_includes_token_info(self, agent, success_json_response, caplog):
        """Test that logging includes token and turn information."""
        with patch.object(agent, '_run_claude') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(success_json_response)
            mock_run.return_value = mock_result

            agent.send_prompt("test")

            # Check that log includes token and turn info
            log_text = caplog.text
            assert 'Tokens:' in log_text
            assert 'Turns:' in log_text
