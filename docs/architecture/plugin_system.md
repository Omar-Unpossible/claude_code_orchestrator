# Plugin System Architecture

## Overview

The plugin system enables multiple agent implementations (Claude Code, Aider, custom) and LLM providers (Ollama, llama.cpp, vLLM) without modifying core orchestration logic.

## Why Plugins?

**Benefits**:
- ✅ Extensibility: Add new agents without touching core code
- ✅ Testability: Mock agents for unit tests
- ✅ Flexibility: Swap implementations via configuration
- ✅ Community: Enable community contributions
- ✅ Maintainability: Clear separation of concerns

**Cost**: +3 hours upfront implementation
**Savings**: 15-20 hours avoided refactoring when adding new agents

See [`../decisions/001_why_plugins.md`](../decisions/001_why_plugins.md) for detailed rationale.

## Architecture

### Component Diagram

```
┌──────────────────────────────────────────┐
│         Plugin Registry                  │
│  ┌────────────────────────────────────┐ │
│  │  AgentRegistry                     │ │
│  │  - register(name, class)           │ │
│  │  - get(name) -> class              │ │
│  │  - list() -> [names]               │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  LLMRegistry                       │ │
│  │  - register(name, class)           │ │
│  │  - get(name) -> class              │ │
│  │  - list() -> [names]               │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐    ┌────────────────┐
│ AgentPlugin   │    │  LLMPlugin     │
│ (ABC)         │    │  (ABC)         │
└───────┬───────┘    └────────┬───────┘
        │                     │
  ┌─────┴─────┐         ┌─────┴─────┐
  ▼           ▼         ▼           ▼
┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
│Claude│  │Aider │  │Ollama│  │Llama │
│ Code │  │Agent │  │ LLM  │  │ .cpp │
└──────┘  └──────┘  └──────┘  └──────┘
```

## Plugin Interfaces

### AgentPlugin (Abstract Base Class)

**Purpose**: Interface for all coding agents

**Required Methods**:
```python
def initialize(self, config: dict) -> None:
    """Set up agent with configuration"""

def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    """Send prompt and return response"""

def get_workspace_files(self) -> List[Path]:
    """Get list of all files in workspace"""

def read_file(self, path: Path) -> str:
    """Read file contents"""

def write_file(self, path: Path, content: str) -> None:
    """Write file contents"""

def get_file_changes(self, since: Optional[float] = None) -> List[dict]:
    """Get files modified since timestamp"""

def is_healthy(self) -> bool:
    """Check if agent is responsive"""

def cleanup(self) -> None:
    """Release resources"""
```

**Optional Methods**:
```python
def get_capabilities(self) -> dict:
    """Return agent capabilities (has default implementation)"""
```

**See**: [`../../src/plugins/base.py`](../../src/plugins/base.py) for complete interface

### LLMPlugin (Abstract Base Class)

**Purpose**: Interface for local LLM providers

**Required Methods**:
```python
def initialize(self, config: dict) -> None:
    """Initialize LLM provider"""

def generate(self, prompt: str, **kwargs) -> str:
    """Generate text completion"""

def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
    """Generate with streaming"""

def estimate_tokens(self, text: str) -> int:
    """Estimate token count"""

def is_available(self) -> bool:
    """Check if LLM is accessible"""
```

**Optional Methods**:
```python
def get_model_info(self) -> dict:
    """Return model information (has default implementation)"""
```

## Registration System

### Decorator-Based Registration

Plugins self-register using decorators:

```python
from src.plugins import register_agent, AgentPlugin

@register_agent('my-agent')
class MyAgent(AgentPlugin):
    def initialize(self, config: dict) -> None:
        self.config = config

    def send_prompt(self, prompt: str, context=None) -> str:
        # Implementation
        return "response"

    # ... implement other methods
```

### Registry Operations

**Register**:
```python
AgentRegistry.register('agent-name', AgentClass)
```

**Retrieve**:
```python
agent_class = AgentRegistry.get('agent-name')
agent = agent_class()
agent.initialize(config)
```

**List**:
```python
available = AgentRegistry.list()
# ['claude-code-ssh', 'aider', 'mock']
```

**Unregister** (for testing):
```python
AgentRegistry.unregister('agent-name')
```

### Thread Safety

Both registries are thread-safe using `RLock`:
- Safe to register from multiple threads
- Safe to retrieve concurrently
- No race conditions

## Configuration-Driven Selection

Plugins are selected via configuration, not code changes:

**config.yaml**:
```yaml
orchestrator:
  agent:
    type: claude-code-ssh  # or: claude-code-docker, aider
    config:
      host: 192.168.1.100
      user: claude
      key_path: ~/.ssh/vm_key
      workspace_path: /home/claude/workspace

  llm:
    type: ollama  # or: llamacpp, vllm
    config:
      model: qwen2.5-coder:32b
      api_url: http://localhost:11434
      temperature: 0.7
```

**Loading**:
```python
config = Config.load('config.yaml')

# Load agent
agent_type = config.get('orchestrator.agent.type')
agent_class = AgentRegistry.get(agent_type)
agent = agent_class()
agent.initialize(config.get('orchestrator.agent.config'))

# Load LLM
llm_type = config.get('orchestrator.llm.type')
llm_class = LLMRegistry.get(llm_type)
llm = llm_class()
llm.initialize(config.get('orchestrator.llm.config'))
```

## Creating a New Plugin

### Step 1: Implement the Interface

```python
# src/agents/my_custom_agent.py

from pathlib import Path
from typing import List, Optional, Dict, Any
from src.plugins import AgentPlugin, register_agent

@register_agent('custom-agent')
class CustomAgent(AgentPlugin):
    """My custom agent implementation."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize agent."""
        self.config = config
        # Setup connection, workspace, etc.

    def send_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Send prompt to agent."""
        # Your implementation
        return "agent response"

    def get_workspace_files(self) -> List[Path]:
        """Get workspace files."""
        # Your implementation
        return []

    def read_file(self, path: Path) -> str:
        """Read file."""
        # Your implementation
        with open(path) as f:
            return f.read()

    def write_file(self, path: Path, content: str) -> None:
        """Write file."""
        # Your implementation
        path.write_text(content)

    def get_file_changes(self, since: Optional[float] = None) -> List[Dict]:
        """Get file changes."""
        # Your implementation
        return []

    def is_healthy(self) -> bool:
        """Check health."""
        return True

    def cleanup(self) -> None:
        """Cleanup."""
        # Close connections, release resources
        pass
```

### Step 2: Import to Register

The `@register_agent` decorator automatically registers your plugin when the module is imported.

**In `src/agents/__init__.py`**:
```python
from src.agents.my_custom_agent import CustomAgent
```

### Step 3: Configure and Use

**config.yaml**:
```yaml
orchestrator:
  agent:
    type: custom-agent
    config:
      # Your custom config
      option1: value1
```

**That's it!** The orchestrator will now use your custom agent.

## Testing Plugins

### Mock Plugins for Testing

Use provided mocks for unit tests:

```python
from tests.mocks import MockAgent, MockLLM

def test_orchestrator():
    # Use mock instead of real agent
    agent = MockAgent()
    agent.initialize({})
    agent.set_response("Expected response")

    # Test your code
    response = agent.send_prompt("test")
    assert response == "Expected response"
```

### Creating Test Doubles

```python
from src.plugins import AgentPlugin, register_agent

@register_agent('test-agent')
class TestAgent(AgentPlugin):
    """Test double for specific test scenario."""

    def __init__(self):
        self.calls = []

    def send_prompt(self, prompt: str, context=None) -> str:
        self.calls.append(('send_prompt', prompt, context))
        return "test response"

    # ... minimal implementation for testing
```

## Validation

### Automatic Validation

Registries validate that plugins implement the required interface:

```python
@register_agent('incomplete')
class IncompleteAgent(AgentPlugin):
    # Missing methods
    def initialize(self, config):
        pass

# Registration with validation=True will check interface
# Instantiation will fail with TypeError due to ABC
```

### Manual Validation

```python
from src.plugins.registry import AgentRegistry

AgentRegistry.register('my-agent', MyAgentClass, validate=True)
# Raises PluginValidationError if interface not implemented
```

## Best Practices

### Do's
✅ Use type hints throughout
✅ Document all public methods
✅ Handle errors gracefully with proper exceptions
✅ Implement `cleanup()` to release resources
✅ Make `is_healthy()` fast (<1s)
✅ Use configuration for all settings
✅ Log important operations at DEBUG level

### Don'ts
❌ Don't hardcode credentials in plugin code
❌ Don't block indefinitely (use timeouts)
❌ Don't modify global state
❌ Don't raise bare exceptions (use typed exceptions)
❌ Don't skip `cleanup()` implementation
❌ Don't assume single-threaded execution

## Exception Handling

All plugins should use the exception hierarchy:

```python
from src.plugins.exceptions import (
    AgentException,
    AgentConnectionException,
    AgentTimeoutException,
    AgentProcessException
)

def send_prompt(self, prompt: str, context=None) -> str:
    try:
        # Send prompt
        response = self._send(prompt)
        return response
    except socket.timeout:
        raise AgentTimeoutException(
            operation='send_prompt',
            timeout_seconds=30,
            agent_type='my-agent'
        )
    except ConnectionError as e:
        raise AgentConnectionException(
            agent_type='my-agent',
            host=self.host,
            details=str(e)
        )
```

## Performance Considerations

### Lazy Initialization
Don't connect in `__init__()`, connect in `initialize()`:
```python
def __init__(self):
    self.connection = None  # Not connected yet

def initialize(self, config):
    self.connection = establish_connection(config)  # Connect here
```

### Connection Pooling
Reuse connections when possible:
```python
def initialize(self, config):
    self.pool = ConnectionPool(max_size=5)
```

### Caching
Cache expensive operations:
```python
@lru_cache(maxsize=100)
def estimate_tokens(self, text: str) -> int:
    # Expensive operation
    return slow_tokenization(text)
```

## Common Pitfalls

### Pitfall 1: Not Implementing All Methods
❌ Missing methods cause `TypeError` at instantiation
✅ Implement all abstract methods, even if minimal

### Pitfall 2: Forgetting Cleanup
❌ Resources leak (connections, files, processes)
✅ Always implement `cleanup()` properly

### Pitfall 3: Blocking Operations
❌ `is_healthy()` takes 30 seconds
✅ Make health checks fast (<1s)

### Pitfall 4: Ignoring Context
❌ Ignore `context` parameter in `send_prompt()`
✅ Use context for timeouts, constraints, task info

### Pitfall 5: Poor Error Messages
❌ `raise Exception("Error")`
✅ Use typed exceptions with context and recovery suggestions

## Examples

See:
- [`../../tests/mocks/`](../../tests/mocks/) - Mock implementations
- [`../../src/agents/`](../../src/agents/) - Real agent implementations (M2+)
- [`../../src/llm/`](../../src/llm/) - Real LLM implementations (M2+)
