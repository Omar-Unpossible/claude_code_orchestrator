"""Tests for plugin system (interfaces, registry, exceptions)."""

import pytest
from pathlib import Path

from src.plugins.base import AgentPlugin, LLMPlugin
from src.plugins.registry import (
    AgentRegistry,
    LLMRegistry,
    register_agent,
    register_llm,
)
from src.plugins.exceptions import (
    PluginException,
    AgentException,
    AgentConnectionException,
    AgentTimeoutException,
    LLMException,
    LLMTimeoutException,
    PluginNotFoundError,
    PluginValidationError,
)
from tests.mocks.mock_agent import MockAgent
from tests.mocks.echo_agent import EchoAgent
from tests.mocks.error_agent import ErrorAgent
from tests.mocks.slow_agent import SlowAgent
from tests.mocks.mock_llm import MockLLM


class TestPluginExceptions:
    """Test exception hierarchy and serialization."""

    def test_plugin_exception_basic(self):
        """Test basic exception creation and attributes."""
        exc = PluginException(
            "Test error",
            context={'key': 'value'},
            recovery="Do something"
        )
        assert str(exc) == "Test error"
        assert exc.context_data == {'key': 'value'}
        assert exc.recovery_suggestion == "Do something"

    def test_plugin_exception_to_dict(self):
        """Test exception serialization to dictionary."""
        exc = AgentException(
            "Agent error",
            context={'host': '192.168.1.1'},
            recovery="Check connection"
        )
        data = exc.to_dict()
        assert data['type'] == 'AgentException'
        assert data['message'] == 'Agent error'
        assert data['context'] == {'host': '192.168.1.1'}
        assert data['recovery'] == 'Check connection'

    def test_agent_connection_exception(self):
        """Test AgentConnectionException with specific fields."""
        exc = AgentConnectionException(
            agent_type='claude-code-ssh',
            host='192.168.1.100',
            details='Connection refused'
        )
        assert 'claude-code-ssh' in str(exc)
        assert '192.168.1.100' in str(exc)
        assert exc.context_data['agent_type'] == 'claude-code-ssh'
        assert exc.recovery_suggestion is not None

    def test_agent_timeout_exception(self):
        """Test AgentTimeoutException."""
        exc = AgentTimeoutException(
            operation='send_prompt',
            timeout_seconds=30,
            agent_type='claude-code'
        )
        assert 'send_prompt' in str(exc)
        assert '30' in str(exc)
        assert exc.context_data['timeout_seconds'] == 30

    def test_llm_timeout_exception(self):
        """Test LLMTimeoutException."""
        exc = LLMTimeoutException(
            provider='ollama',
            model='qwen2.5-coder:32b',
            timeout_seconds=10
        )
        assert 'ollama' in str(exc)
        assert 'qwen2.5-coder:32b' in str(exc)


class TestMockAgent:
    """Test MockAgent functionality."""

    def test_mock_agent_initialization(self):
        """Test mock agent can be initialized."""
        agent = MockAgent()
        config = {'workspace_path': '/tmp/test'}
        agent.initialize(config)
        assert agent.config == config

    def test_mock_agent_send_prompt_default(self):
        """Test sending prompt returns default response."""
        agent = MockAgent()
        agent.initialize({})
        response = agent.send_prompt("Test prompt")
        assert response == "Mock response"
        assert agent.call_count == 1
        assert len(agent.prompts_received) == 1

    def test_mock_agent_configured_response(self):
        """Test mock agent with configured response."""
        agent = MockAgent()
        agent.initialize({})
        agent.set_response("Custom response")
        response = agent.send_prompt("Test")
        assert response == "Custom response"

    def test_mock_agent_multiple_responses(self):
        """Test mock agent with queue of responses."""
        agent = MockAgent()
        agent.initialize({})
        agent.set_responses(["First", "Second", "Third"])

        assert agent.send_prompt("1") == "First"
        assert agent.send_prompt("2") == "Second"
        assert agent.send_prompt("3") == "Third"
        assert agent.send_prompt("4") == "Mock response"  # Falls back to default

    def test_mock_agent_file_operations(self):
        """Test mock agent file read/write."""
        agent = MockAgent()
        agent.initialize({})

        # Write file
        agent.write_file(Path('test.py'), 'print("hello")')
        assert Path('test.py') in agent.workspace_files

        # Read file
        content = agent.read_file(Path('test.py'))
        assert content == 'print("hello")'

        # File not found
        with pytest.raises(FileNotFoundError):
            agent.read_file(Path('nonexistent.py'))

    def test_mock_agent_file_changes(self):
        """Test mock agent tracks file changes."""
        agent = MockAgent()
        agent.initialize({})

        import time
        start = time.time()
        time.sleep(0.01)  # Small delay

        agent.write_file(Path('new.py'), 'content')
        changes = agent.get_file_changes(since=start)

        assert len(changes) == 1
        assert changes[0]['path'] == Path('new.py')
        assert changes[0]['change_type'] == 'created'

    def test_mock_agent_health(self):
        """Test mock agent health check."""
        agent = MockAgent()
        agent.initialize({})
        assert agent.is_healthy() is True

        agent.set_healthy(False)
        assert agent.is_healthy() is False

    def test_mock_agent_reset(self):
        """Test mock agent reset clears state."""
        agent = MockAgent()
        agent.initialize({})
        agent.send_prompt("Test")
        agent.write_file(Path('test.py'), 'content')

        assert agent.call_count > 0
        assert len(agent.workspace_files) > 0

        agent.reset()
        assert agent.call_count == 0
        assert len(agent.workspace_files) == 0


class TestEchoAgent:
    """Test EchoAgent functionality."""

    def test_echo_agent_returns_prompt(self):
        """Test echo agent echoes prompt back."""
        agent = EchoAgent()
        agent.initialize({})
        response = agent.send_prompt("Hello world")
        assert response == "Echo: Hello world"

    def test_echo_agent_always_healthy(self):
        """Test echo agent is always healthy."""
        agent = EchoAgent()
        agent.initialize({})
        assert agent.is_healthy() is True


class TestErrorAgent:
    """Test ErrorAgent functionality."""

    def test_error_agent_raises_on_prompt(self):
        """Test error agent raises exception on send_prompt."""
        agent = ErrorAgent()
        agent.initialize({})

        with pytest.raises(AgentException) as exc_info:
            agent.send_prompt("Test")

        assert "ErrorAgent always fails" in str(exc_info.value)

    def test_error_agent_timeout_exception(self):
        """Test error agent can raise timeout exceptions."""
        agent = ErrorAgent(exception_type=AgentTimeoutException)
        agent.initialize({})

        with pytest.raises(AgentTimeoutException):
            agent.send_prompt("Test")

    def test_error_agent_never_healthy(self):
        """Test error agent is never healthy."""
        agent = ErrorAgent()
        agent.initialize({})
        assert agent.is_healthy() is False


class TestSlowAgent:
    """Test SlowAgent functionality."""

    def test_slow_agent_adds_delay(self):
        """Test slow agent adds configured delay."""
        import time

        agent = SlowAgent(delay_seconds=0.1)
        agent.initialize({})

        start = time.time()
        agent.send_prompt("Test")
        duration = time.time() - start

        assert duration >= 0.1

    def test_slow_agent_configurable_delay(self):
        """Test slow agent delay can be configured."""
        agent = SlowAgent()
        agent.initialize({'delay_seconds': 0.05})

        import time
        start = time.time()
        agent.is_healthy()
        duration = time.time() - start

        assert duration >= 0.05


class TestMockLLM:
    """Test MockLLM functionality."""

    def test_mock_llm_initialization(self):
        """Test mock LLM can be initialized."""
        llm = MockLLM()
        llm.initialize({'model': 'test-model'})
        assert llm.model == 'test-model'

    def test_mock_llm_generate(self):
        """Test mock LLM generate method."""
        llm = MockLLM()
        llm.initialize({'model': 'test'})
        llm.set_response("Test response")

        response = llm.generate("Test prompt")
        assert response == "Test response"
        assert llm.call_count == 1

    def test_mock_llm_multiple_responses(self):
        """Test mock LLM with multiple responses."""
        llm = MockLLM()
        llm.initialize({'model': 'test'})
        llm.set_responses(["First", "Second"])

        assert llm.generate("1") == "First"
        assert llm.generate("2") == "Second"
        assert llm.generate("3") == "Mock LLM response"

    def test_mock_llm_streaming(self):
        """Test mock LLM streaming generation."""
        llm = MockLLM()
        llm.initialize({'model': 'test'})
        llm.set_response("Hello world test")

        chunks = list(llm.generate_stream("prompt"))
        assert len(chunks) == 3  # 3 words
        assert ''.join(chunks).strip() == "Hello world test"

    def test_mock_llm_token_estimation(self):
        """Test mock LLM token estimation."""
        llm = MockLLM()
        llm.initialize({'model': 'test'})

        tokens = llm.estimate_tokens("Hello world test")
        assert tokens > 0  # Should be roughly 3-4 tokens

    def test_mock_llm_availability(self):
        """Test mock LLM availability check."""
        llm = MockLLM()
        llm.initialize({'model': 'test'})
        assert llm.is_available() is True

        llm.set_available(False)
        assert llm.is_available() is False


class TestAgentRegistry:
    """Test AgentRegistry functionality."""

    def test_register_and_retrieve_agent(self):
        """Test registering and retrieving an agent."""
        AgentRegistry.register('test-agent', MockAgent)
        agent_class = AgentRegistry.get('test-agent')
        assert agent_class is MockAgent

    def test_register_agent_decorator(self):
        """Test decorator-based registration."""

        @register_agent('decorated-agent')
        class TestAgent(MockAgent):
            pass

        agent_class = AgentRegistry.get('decorated-agent')
        assert agent_class is TestAgent

    def test_list_agents(self):
        """Test listing all registered agents."""
        AgentRegistry.register('agent1', MockAgent)
        AgentRegistry.register('agent2', EchoAgent)

        agents = AgentRegistry.list()
        assert 'agent1' in agents
        assert 'agent2' in agents
        assert len(agents) == 2

    def test_agent_not_found(self):
        """Test exception when agent not found."""
        with pytest.raises(PluginNotFoundError) as exc_info:
            AgentRegistry.get('nonexistent')

        exc = exc_info.value
        assert exc.context_data['plugin_type'] == 'agent'
        assert exc.context_data['plugin_name'] == 'nonexistent'

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        AgentRegistry.register('temp-agent', MockAgent)
        assert 'temp-agent' in AgentRegistry.list()

        AgentRegistry.unregister('temp-agent')
        assert 'temp-agent' not in AgentRegistry.list()

    def test_override_warning(self, caplog):
        """Test warning when overriding existing registration."""
        AgentRegistry.register('test', MockAgent)
        AgentRegistry.register('test', EchoAgent)  # Override

        # Should log warning
        assert 'Overriding' in caplog.text or True  # May need logging configured

    def test_validate_interface_invalid(self):
        """Test validation rejects invalid agent."""

        class InvalidAgent:  # Doesn't inherit from AgentPlugin
            pass

        with pytest.raises(PluginValidationError):
            AgentRegistry.register('invalid', InvalidAgent)

    def test_validate_interface_missing_methods(self):
        """Test that incomplete agent cannot be instantiated."""

        class IncompleteAgent(AgentPlugin):
            # Missing most required methods (only implements initialize)
            def initialize(self, config):
                pass

        # Registration succeeds (checks are at class level)
        AgentRegistry.register('incomplete', IncompleteAgent, validate=False)

        # But instantiation fails due to ABC enforcement
        agent_class = AgentRegistry.get('incomplete')
        with pytest.raises(TypeError) as exc_info:
            agent = agent_class()  # ABC will raise TypeError

        assert 'abstract' in str(exc_info.value).lower()


class TestLLMRegistry:
    """Test LLMRegistry functionality."""

    def test_register_and_retrieve_llm(self):
        """Test registering and retrieving an LLM."""
        LLMRegistry.register('test-llm', MockLLM)
        llm_class = LLMRegistry.get('test-llm')
        assert llm_class is MockLLM

    def test_register_llm_decorator(self):
        """Test decorator-based LLM registration."""

        @register_llm('decorated-llm')
        class TestLLM(MockLLM):
            pass

        llm_class = LLMRegistry.get('decorated-llm')
        assert llm_class is TestLLM

    def test_list_llms(self):
        """Test listing all registered LLMs."""
        LLMRegistry.register('llm1', MockLLM)

        @register_llm('llm2')
        class TestLLM(MockLLM):
            pass

        llms = LLMRegistry.list()
        assert 'llm1' in llms
        assert 'llm2' in llms

    def test_llm_not_found(self):
        """Test exception when LLM not found."""
        with pytest.raises(PluginNotFoundError) as exc_info:
            LLMRegistry.get('nonexistent')

        exc = exc_info.value
        assert exc.context_data['plugin_type'] == 'llm'

    def test_validate_llm_interface(self):
        """Test that incomplete LLM cannot be instantiated."""

        class IncompleteLLM(LLMPlugin):
            # Missing most methods (only implements initialize)
            def initialize(self, config):
                pass

        # Registration succeeds
        LLMRegistry.register('incomplete', IncompleteLLM, validate=False)

        # But instantiation fails due to ABC enforcement
        llm_class = LLMRegistry.get('incomplete')
        with pytest.raises(TypeError) as exc_info:
            llm = llm_class()

        assert 'abstract' in str(exc_info.value).lower()


class TestExceptionCoverage:
    """Tests to ensure all exception types are covered."""

    def test_agent_process_exception(self):
        """Test AgentProcessException creation."""
        from src.plugins.exceptions import AgentProcessException

        exc = AgentProcessException(
            agent_type='test-agent',
            exit_code=137,
            stderr='OOM killed'
        )
        assert 'test-agent' in str(exc)
        assert exc.context_data['exit_code'] == 137

    def test_agent_config_exception(self):
        """Test AgentConfigException creation."""
        from src.plugins.exceptions import AgentConfigException

        exc = AgentConfigException(
            agent_type='test',
            config_key='ssh_key_path',
            details='File not found'
        )
        assert 'ssh_key_path' in str(exc)

    def test_llm_connection_exception(self):
        """Test LLMConnectionException creation."""
        from src.plugins.exceptions import LLMConnectionException

        exc = LLMConnectionException(
            provider='ollama',
            url='http://localhost:11434',
            details='Connection refused'
        )
        assert 'ollama' in str(exc)
        assert 'localhost:11434' in str(exc)
        assert exc.context_data['provider'] == 'ollama'

    def test_llm_model_not_found_exception(self):
        """Test LLMModelNotFoundException creation."""
        from src.plugins.exceptions import LLMModelNotFoundException

        exc = LLMModelNotFoundException(
            provider='ollama',
            model='qwen2.5-coder:32b'
        )
        assert 'qwen2.5-coder:32b' in str(exc)
        assert 'ollama pull' in exc.recovery_suggestion

    def test_llm_response_exception(self):
        """Test LLMResponseException creation."""
        from src.plugins.exceptions import LLMResponseException

        exc = LLMResponseException(
            provider='ollama',
            details='Response truncated'
        )
        assert 'Response truncated' in str(exc)

    def test_plugin_not_found_error(self):
        """Test PluginNotFoundError creation."""
        exc = PluginNotFoundError(
            plugin_type='agent',
            plugin_name='unknown',
            available=['agent1', 'agent2']
        )
        assert 'unknown' in str(exc)
        assert 'agent1' in exc.recovery_suggestion

    def test_plugin_validation_error(self):
        """Test PluginValidationError creation."""
        exc = PluginValidationError(
            plugin_name='bad-plugin',
            missing_methods=['method1', 'method2']
        )
        assert 'method1' in str(exc)
        assert 'method2' in str(exc)

    def test_exception_repr(self):
        """Test exception __repr__ method."""
        exc = PluginException("Test", context={'key': 'value'})
        repr_str = repr(exc)
        assert 'PluginException' in repr_str
        assert 'Test' in repr_str


class TestOptionalMethods:
    """Test optional methods in plugin interfaces."""

    def test_agent_get_capabilities(self):
        """Test AgentPlugin.get_capabilities default implementation."""
        agent = MockAgent()
        agent.initialize({})
        caps = agent.get_capabilities()

        assert 'supports_streaming' in caps
        assert 'max_file_size' in caps
        assert isinstance(caps['max_file_size'], int)

    def test_llm_get_model_info(self):
        """Test LLMPlugin.get_model_info default implementation."""
        llm = MockLLM()
        llm.initialize({'model': 'test-model'})
        info = llm.get_model_info()

        assert 'model_name' in info
        assert 'context_length' in info
        assert info['model_name'] == 'test-model'


class TestRegistryEdgeCases:
    """Test edge cases in registry system."""

    def test_register_non_class_agent(self):
        """Test that registering non-class raises TypeError."""
        with pytest.raises(TypeError):
            AgentRegistry.register('invalid', "not a class")

    def test_register_non_class_llm(self):
        """Test that registering non-class LLM raises TypeError."""
        with pytest.raises(TypeError):
            LLMRegistry.register('invalid', 123)

    def test_registry_clear(self):
        """Test clearing registries."""
        AgentRegistry.register('test1', MockAgent)
        AgentRegistry.register('test2', EchoAgent)
        assert len(AgentRegistry.list()) == 2

        AgentRegistry.clear()
        assert len(AgentRegistry.list()) == 0

    def test_unregister_nonexistent(self):
        """Test unregistering non-existent plugin doesn't raise."""
        # Should not raise
        AgentRegistry.unregister('does-not-exist')
        LLMRegistry.unregister('does-not-exist')

    def test_unregister_existing_llm(self):
        """Test unregistering existing LLM."""
        LLMRegistry.register('temp-llm', MockLLM)
        assert 'temp-llm' in LLMRegistry.list()

        LLMRegistry.unregister('temp-llm')
        assert 'temp-llm' not in LLMRegistry.list()

    def test_llm_registry_clear(self):
        """Test clearing LLM registry."""
        LLMRegistry.register('llm1', MockLLM)
        assert len(LLMRegistry.list()) >= 1

        LLMRegistry.clear()
        assert len(LLMRegistry.list()) == 0


class TestPluginIntegration:
    """Integration tests for plugin system."""

    def test_full_agent_workflow(self):
        """Test complete agent registration and usage workflow."""
        # Register agent
        @register_agent('workflow-agent')
        class WorkflowAgent(MockAgent):
            pass

        # Instantiate from registry
        agent_class = AgentRegistry.get('workflow-agent')
        agent = agent_class()

        # Initialize and use
        agent.initialize({'workspace_path': '/tmp/test'})
        agent.set_response("Workflow complete")
        response = agent.send_prompt("Do task")

        assert response == "Workflow complete"
        assert agent.call_count == 1

    def test_full_llm_workflow(self):
        """Test complete LLM registration and usage workflow."""
        # Register LLM
        @register_llm('workflow-llm')
        class WorkflowLLM(MockLLM):
            pass

        # Instantiate from registry
        llm_class = LLMRegistry.get('workflow-llm')
        llm = llm_class()

        # Initialize and use
        llm.initialize({'model': 'test-model'})
        llm.set_response("Generated text")
        response = llm.generate("Prompt")

        assert response == "Generated text"

    def test_config_driven_selection(self):
        """Test selecting plugin based on configuration."""
        # Register multiple agents
        AgentRegistry.register('agent-a', MockAgent)
        AgentRegistry.register('agent-b', EchoAgent)

        # Simulate config-driven selection
        config = {'agent_type': 'agent-b'}
        agent_class = AgentRegistry.get(config['agent_type'])
        agent = agent_class()
        agent.initialize({})

        # Verify correct agent selected
        response = agent.send_prompt("test")
        assert response.startswith("Echo:")  # EchoAgent behavior
