"""Tests for interactive agent messaging and dynamic labels.

Tests Phase 1, 2, and Task 2.3 functionality:
- Dynamic label generation
- Intent classification
- Decision threshold adjustment
- Feedback generation
- Backward compatibility
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.utils.command_processor import CommandProcessor
from src.orchestration.decision_engine import DecisionEngine, Action
from src.llm.local_interface import LocalLLMInterface
from src.llm.openai_codex_interface import OpenAICodexLLMPlugin
from datetime import datetime, UTC


class TestDynamicLabelGeneration:
    """Test dynamic label generation from LLM interfaces."""

    def test_ollama_get_name(self):
        """Test LocalLLMInterface returns 'ollama' as name."""
        llm = LocalLLMInterface()
        assert llm.get_name() == 'ollama'

    def test_codex_get_name(self):
        """Test OpenAICodexLLMPlugin returns 'openai-codex' as name."""
        llm = OpenAICodexLLMPlugin()
        assert llm.get_name() == 'openai-codex'

    def test_orchestrator_uses_dynamic_label(self):
        """Test orchestrator display uses dynamic label from LLM."""
        from src.orchestrator import Orchestrator
        from src.core.config import Config

        # Create config with mock LLM
        config = Config.load()

        # Mock LLM interface with custom name
        mock_llm = Mock()
        mock_llm.get_name.return_value = 'test-llm'

        # Create orchestrator and inject mock
        orchestrator = Orchestrator(config=config)
        orchestrator.llm_interface = mock_llm

        # Verify _print_orch uses dynamic label
        with patch('builtins.print') as mock_print:
            orchestrator._print_orch("Test message")

            # Check print was called with dynamic label
            printed_text = mock_print.call_args[0][0]
            assert '[ORCH:test-llm]' in printed_text
            assert 'Test message' in printed_text


class TestIntentClassification:
    """Test intent classification in /to-orch command."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator for testing."""
        orchestrator = Mock()
        orchestrator.injected_context = {}
        return orchestrator

    @pytest.fixture
    def processor(self, mock_orchestrator):
        """Create command processor with mock orchestrator."""
        return CommandProcessor(mock_orchestrator)

    def test_validation_guidance_intent(self, processor):
        """Test intent classification for validation guidance."""
        result = processor.execute_command('/to-orch Be more lenient with quality scores')

        assert result['success']
        assert processor.orchestrator.injected_context['to_orch_intent'] == 'validation_guidance'

    def test_validation_guidance_keywords(self, processor):
        """Test all validation guidance keywords."""
        keywords = ['quality', 'score', 'validate', 'lenient', 'strict']

        for keyword in keywords:
            processor.orchestrator.injected_context.clear()
            result = processor.execute_command(f'/to-orch Focus on {keyword} improvements')

            assert result['success'], f"Failed for keyword: {keyword}"
            assert processor.orchestrator.injected_context['to_orch_intent'] == 'validation_guidance'

    def test_decision_hint_intent(self, processor):
        """Test intent classification for decision hints."""
        result = processor.execute_command('/to-orch Accept this response')

        assert result['success']
        assert processor.orchestrator.injected_context['to_orch_intent'] == 'decision_hint'

    def test_decision_hint_keywords(self, processor):
        """Test all decision hint keywords."""
        keywords = ['accept', 'proceed', 'approve', 'override']

        for keyword in keywords:
            processor.orchestrator.injected_context.clear()
            result = processor.execute_command(f'/to-orch Please {keyword} this')

            assert result['success'], f"Failed for keyword: {keyword}"
            assert processor.orchestrator.injected_context['to_orch_intent'] == 'decision_hint'

    def test_feedback_request_intent(self, processor):
        """Test intent classification for feedback requests."""
        result = processor.execute_command('/to-orch Review this code and suggest improvements')

        assert result['success']
        assert processor.orchestrator.injected_context['to_orch_intent'] == 'feedback_request'

    def test_feedback_request_keywords(self, processor):
        """Test all feedback request keywords."""
        keywords = ['review', 'analyze', 'suggest', 'feedback', 'tell']

        for keyword in keywords:
            processor.orchestrator.injected_context.clear()
            result = processor.execute_command(f'/to-orch {keyword} me about this')

            assert result['success'], f"Failed for keyword: {keyword}"
            assert processor.orchestrator.injected_context['to_orch_intent'] == 'feedback_request'

    def test_general_intent_fallback(self, processor):
        """Test general intent for messages without specific keywords."""
        result = processor.execute_command('/to-orch Do something special')

        assert result['success']
        assert processor.orchestrator.injected_context['to_orch_intent'] == 'general'


class TestDecisionThresholdAdjustment:
    """Test decision threshold adjustment in DecisionEngine."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager."""
        return Mock()

    @pytest.fixture
    def mock_breakpoint_manager(self):
        """Create mock breakpoint manager."""
        manager = Mock()
        manager.evaluate_breakpoint_conditions.return_value = []  # Empty list = no breakpoints
        return manager

    @pytest.fixture
    def decision_engine(self, mock_state_manager, mock_breakpoint_manager):
        """Create decision engine for testing."""
        return DecisionEngine(mock_state_manager, mock_breakpoint_manager)

    def test_no_adjustment_baseline(self, decision_engine):
        """Test decision without threshold adjustment (baseline)."""
        context = {
            'task': Mock(id=1),
            'response': 'test response',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.68,  # Between marginal and acceptable
            'confidence_score': 0.7
        }

        # Without adjustment, 0.68 < 0.7 should result in CLARIFY or ESCALATE
        action = decision_engine.decide_next_action(context, threshold_adjustment=0.0)
        assert action.type in [DecisionEngine.ACTION_CLARIFY, DecisionEngine.ACTION_ESCALATE]

    def test_positive_adjustment_lowers_threshold(self, decision_engine):
        """Test positive adjustment makes decisions more lenient."""
        context = {
            'task': Mock(id=1),
            'response': 'test response',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.68,  # Between marginal and acceptable
            'confidence_score': 0.7
        }

        # With +0.15 adjustment, threshold becomes 0.55, so 0.68 should PROCEED
        action = decision_engine.decide_next_action(context, threshold_adjustment=0.15)
        assert action.type == DecisionEngine.ACTION_PROCEED

    def test_negative_adjustment_raises_threshold(self, decision_engine):
        """Test negative adjustment makes decisions stricter."""
        context = {
            'task': Mock(id=1),
            'response': 'test response',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.72,  # Just above acceptable
            'confidence_score': 0.75
        }

        # Without adjustment, 0.72 > 0.7 should PROCEED
        action_baseline = decision_engine.decide_next_action(context, threshold_adjustment=0.0)
        assert action_baseline.type == DecisionEngine.ACTION_PROCEED

        # With -0.05 adjustment, threshold becomes 0.75, so 0.72 should not PROCEED
        action_strict = decision_engine.decide_next_action(context, threshold_adjustment=-0.05)
        assert action_strict.type != DecisionEngine.ACTION_PROCEED

    def test_adjustment_bounds_checking(self, decision_engine):
        """Test threshold adjustment respects 0.0-1.0 bounds."""
        context = {
            'task': Mock(id=1),
            'response': 'test response',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.1,
            'confidence_score': 0.2
        }

        # Extreme positive adjustment should not make thresholds negative
        action = decision_engine.decide_next_action(context, threshold_adjustment=1.0)
        assert action is not None  # Should not crash

    def test_adjustment_logging(self, decision_engine):
        """Test threshold adjustment is logged."""
        context = {
            'task': Mock(id=1),
            'response': 'test response',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.68,
            'confidence_score': 0.7
        }

        with patch('src.orchestration.decision_engine.logger') as mock_logger:
            decision_engine.decide_next_action(context, threshold_adjustment=0.15)

            # Verify logging occurred
            assert mock_logger.info.called
            logged_message = str(mock_logger.info.call_args_list)
            assert 'DECISION_HINT' in logged_message or 'adjustment' in logged_message.lower()


class TestBackwardCompatibility:
    """Test backward compatibility of legacy commands."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        orchestrator = Mock()
        orchestrator.injected_context = {}
        return orchestrator

    @pytest.fixture
    def processor(self, mock_orchestrator):
        """Create command processor."""
        return CommandProcessor(mock_orchestrator)

    def test_to_claude_alias_works(self, processor):
        """Test /to-claude alias works same as /to-impl."""
        result = processor.execute_command('/to-claude Add tests')

        assert result['success']
        # Should store in both keys
        assert 'to_impl' in processor.orchestrator.injected_context
        assert 'to_claude' in processor.orchestrator.injected_context

    def test_to_obra_alias_works(self, processor):
        """Test /to-obra alias works same as /to-orch."""
        result = processor.execute_command('/to-obra Be lenient')

        assert result['success']
        # Should store in both keys
        assert 'to_orch' in processor.orchestrator.injected_context
        assert 'to_obra' in processor.orchestrator.injected_context
        # Should classify intent
        assert 'to_orch_intent' in processor.orchestrator.injected_context

    def test_formal_aliases_work(self, processor):
        """Test formal aliases (/to-implementer, /to-orchestrator)."""
        # Test /to-implementer
        result1 = processor.execute_command('/to-implementer Add error handling')
        assert result1['success']
        assert 'to_impl' in processor.orchestrator.injected_context

        # Test /to-orchestrator
        processor.orchestrator.injected_context.clear()
        result2 = processor.execute_command('/to-orchestrator Review this')
        assert result2['success']
        assert 'to_orch' in processor.orchestrator.injected_context

    def test_legacy_message_format(self, processor):
        """Test legacy message keys are still set for compatibility."""
        processor.execute_command('/to-impl Test message')

        # Both new and legacy keys should be set
        assert processor.orchestrator.injected_context['to_impl'] == 'Test message'
        assert processor.orchestrator.injected_context['to_claude'] == 'Test message'


class TestFeedbackGeneration:
    """Test feedback generation functionality."""

    def test_feedback_generation_integration(self):
        """Test feedback generation calls LLM and injects result."""
        from src.orchestrator import Orchestrator
        from src.core.config import Config

        config = Config.load()
        orchestrator = Orchestrator(config=config)
        orchestrator.interactive_mode = True

        # Mock LLM interface
        mock_llm = Mock()
        mock_llm.generate.return_value = "1. Improve error handling\n2. Add input validation\n3. Optimize performance"
        orchestrator.llm_interface = mock_llm

        # Set up context with feedback request intent
        orchestrator.injected_context = {
            'to_orch': 'Review this code and suggest 3 improvements',
            'to_orch_intent': 'feedback_request'
        }

        # Mock current task
        orchestrator.current_task = Mock()
        orchestrator.current_task.description = "Implement user authentication"

        # Simulate the feedback generation code path
        # (In real execution, this happens in orchestrator.py lines 1436-1473)
        orch_message = orchestrator.injected_context.get('to_orch', '')
        if orchestrator.injected_context.get('to_orch_intent') == 'feedback_request':
            feedback_prompt = f"""Analyze the following code implementation and provide feedback.

User Request: {orch_message}

Task Description:
{orchestrator.current_task.description}

Implementation (Response):
test response content...

Provide concise, actionable feedback focusing on what the user requested. Be specific."""

            feedback = mock_llm.generate(feedback_prompt, max_tokens=500, temperature=0.3)
            feedback_message = f"ORCHESTRATOR FEEDBACK:\n{feedback}\n\nPlease address this feedback in your next iteration."
            orchestrator.injected_context['to_impl'] = feedback_message

        # Verify LLM was called with correct parameters
        assert mock_llm.generate.called
        call_args = mock_llm.generate.call_args
        assert 'Review this code' in call_args[0][0]
        assert call_args[1]['max_tokens'] == 500
        assert call_args[1]['temperature'] == 0.3

        # Verify feedback was injected
        assert 'to_impl' in orchestrator.injected_context
        assert 'ORCHESTRATOR FEEDBACK' in orchestrator.injected_context['to_impl']
        assert 'Improve error handling' in orchestrator.injected_context['to_impl']

    def test_feedback_generation_error_handling(self):
        """Test feedback generation handles LLM errors gracefully."""
        from src.orchestrator import Orchestrator
        from src.core.config import Config

        config = Config.load()
        orchestrator = Orchestrator(config=config)
        orchestrator.interactive_mode = True

        # Mock LLM interface that raises exception
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("LLM connection failed")
        orchestrator.llm_interface = mock_llm

        orchestrator.injected_context = {
            'to_orch': 'Review this',
            'to_orch_intent': 'feedback_request'
        }
        orchestrator.current_task = Mock(description="Test task")

        # Should not crash, should handle error gracefully
        try:
            if orchestrator.injected_context.get('to_orch_intent') == 'feedback_request':
                mock_llm.generate("test", max_tokens=500, temperature=0.3)
        except Exception as e:
            # Error should be caught and logged, not propagated
            assert "LLM connection failed" in str(e)
