# Flexible LLM Orchestrator Implementation Plan

**Target**: Add multi-provider LLM support for Orchestrator (Orc) with OpenAI Codex CLI as first remote option
**Complexity**: Medium
**Estimated Effort**: 6-8 hours (first provider), 4-6 hours (additional providers)
**Status**: Ready for Implementation

**Reference Guide**: [`docs/research/OpenAI_Codex_CLI_Production_Guide.md`](../research/OpenAI_Codex_CLI_Production_Guide.md) - **READ THIS FIRST** before implementation

---

## Objective

Enable Obra Orchestrator (Orc) to use multiple LLM providers based on configuration. The implementation must:
- Support **multiple provider types**: HTTP API-based (Ollama) and CLI-based (OpenAI Codex CLI)
- Leverage existing `LLMPlugin` interface (no interface changes)
- Use existing `LLMRegistry` for plugin discovery
- Start with **OpenAI Codex CLI** (flat fee subscription, similar to Claude Code CLI)
- Enable easy addition of future providers (Claude API, Mistral API, Gemini API, etc.)
- Maintain 100% backward compatibility with current Qwen setup
- Require zero changes to orchestration logic
- Switch between providers via single config line change

**Important Distinction**:
- **Orc (Orchestrator)**: Uses LLMPlugin for validation/quality scoring (this plan)
- **Imp (Implementer)**: Uses AgentPlugin for code generation (already flexible)

---

## Architecture Context

### Current State
- **Hardcoded instantiation**: `src/orchestrator.py:353` creates `LocalLLMInterface()` directly
- **No registry usage**: LLM not loaded from `LLMRegistry` (unlike agents which use `AgentRegistry`)
- **Working plugin system**: `LLMPlugin` interface exists, `LocalLLMInterface` implements it
- **Single provider**: Only Ollama/Qwen (HTTP API-based) supported

### Target State
- **Registry-based instantiation**: Orchestrator uses `LLMRegistry.get(llm_type)` to load LLM
- **Multi-provider architecture**: Support both HTTP API and CLI-based LLMs
- **Initial registered plugins**:
  - `ollama` → `LocalLLMInterface` (existing, HTTP API-based)
  - `openai-codex` → `OpenAICodexLLMPlugin` (new, CLI-based)
- **Future provider support**:
  - `anthropic` → Claude API (HTTP API-based)
  - `mistral` → Mistral API (HTTP API-based)
  - `gemini` → Google Gemini API (HTTP API-based)
  - `openai-api` → OpenAI API pay-per-token (HTTP API-based)
- **Config-driven selection**: `llm.type: ollama` or `llm.type: openai-codex` or `llm.type: anthropic`, etc.

### Key Principles
1. **Follow agent pattern exactly**: `src/orchestrator.py:371-379` shows correct registry usage for agents. Copy this pattern for LLM.
2. **Support two execution models**:
   - **HTTP API-based**: Direct API calls (Ollama, Claude API, Mistral API)
   - **CLI-based**: Subprocess execution (OpenAI Codex CLI, similar to Claude Code)
3. **Provider-agnostic interface**: `LLMPlugin` works for any provider type

---

## Multi-Provider Architecture

### Provider Types

**Type A: HTTP API-Based LLMs**
- Direct HTTP API calls to LLM service
- Examples: Ollama (local), Claude API, Mistral API, Gemini API, OpenAI API (pay-per-token)
- Implementation: Use `requests` or provider SDK
- Pattern: `LocalLLMInterface` (existing Ollama implementation)

**Type B: CLI-Based LLMs**
- Subprocess execution of CLI tool (like Claude Code for Imp)
- Examples: OpenAI Codex CLI (flat fee subscription)
- Implementation: `subprocess.run()` with stdout parsing
- Pattern: Similar to `ClaudeCodeLocalAgent` but for LLM operations

### Provider Comparison Table

| Provider | Type | Status | Model Examples | Implementation Pattern |
|----------|------|--------|----------------|------------------------|
| **Ollama** | HTTP API | ✅ Implemented | qwen2.5-coder:32b | LocalLLMInterface (HTTP) |
| **OpenAI Codex CLI** | CLI | 🚧 Phase 3 (This Plan) | codex (flat fee) | Subprocess execution |
| **Anthropic Claude** | HTTP API | ⏳ Future | claude-3-5-sonnet | Copy HTTP pattern |
| **Mistral** | HTTP API | ⏳ Future | mistral-large-latest | Copy HTTP pattern |
| **Google Gemini** | HTTP API | ⏳ Future | gemini-1.5-pro | Copy HTTP pattern |
| **OpenAI API** | HTTP API | ⏳ Future | gpt-4o (pay-per-token) | Copy HTTP pattern |
| **Cohere** | HTTP API | ⏳ Future | command-r-plus | Copy HTTP pattern |

### Adding Future Providers

**HTTP API Provider** (4-5 hours):
1. Copy `LocalLLMInterface` structure
2. Replace Ollama HTTP calls with provider SDK
3. Register with `@register_llm('provider-name')`
4. Add tests

**CLI-Based Provider** (5-6 hours):
1. Copy `OpenAICodexLLMPlugin` structure (from this plan)
2. Replace `codex` command with provider CLI command
3. Adjust output parsing for provider format
4. Register with `@register_llm('provider-name')`
5. Add tests

**Configuration Example** (all providers):
```yaml
# Local hardware option
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://172.29.144.1:11434

# Remote CLI option (flat fee subscription)
llm:
  type: openai-codex
  model: codex
  # No API key needed - uses authenticated CLI

# Remote API options (pay-per-token)
llm:
  type: anthropic
  model: claude-3-5-sonnet-20241022
  api_key: ${ANTHROPIC_API_KEY}

llm:
  type: mistral
  model: mistral-large-latest
  api_key: ${MISTRAL_API_KEY}

llm:
  type: gemini
  model: gemini-1.5-pro
  api_key: ${GOOGLE_API_KEY}
```

### Interface Flexibility

The `LLMPlugin` interface is **completely provider-agnostic**:
- No assumptions about HTTP vs CLI
- No assumptions about authentication method
- No assumptions about request/response format
- All providers implement same 5 abstract methods

**This means**: Adding any LLM provider (HTTP or CLI) is just implementing the interface. The orchestrator doesn't know or care about implementation details.

---

## Implementation Phases

### PHASE 1: Register Existing LLM (20 minutes)

**Objective**: Make `LocalLLMInterface` discoverable via `LLMRegistry`

**Files to Modify**:
1. `src/llm/local_interface.py`

**Changes Required**:

**File: `src/llm/local_interface.py`**
- **Line 1-40**: Add import after existing imports
  ```python
  from src.plugins.registry import register_llm
  ```

- **Line 42**: Add decorator above class definition
  ```python
  @register_llm('ollama')
  class LocalLLMInterface(LLMPlugin):
  ```

**Validation**:
- Import `src.llm.local_interface` in Python REPL
- Verify `LLMRegistry.list()` includes `'ollama'`
- Verify `LLMRegistry.get('ollama')` returns `LocalLLMInterface` class

**Success Criteria**:
- ✅ No errors on import
- ✅ `'ollama'` appears in `LLMRegistry.list()`
- ✅ `LLMRegistry.get('ollama')` returns correct class
- ✅ Existing tests still pass (no behavior change)

---

### PHASE 2: Update Orchestrator to Use Registry (30 minutes)

**Objective**: Replace hardcoded `LocalLLMInterface()` with registry lookup

**Files to Modify**:
1. `src/orchestrator.py`

**Changes Required**:

**File: `src/orchestrator.py`**

**Method: `_initialize_llm()` (lines 344-369)**

**Current Code (WRONG)**:
```python
def _initialize_llm(self) -> None:
    """Initialize LLM interface."""
    llm_config = self.config.get('llm', {})

    # Map api_url to endpoint for LocalLLMInterface compatibility
    if 'api_url' in llm_config and 'endpoint' not in llm_config:
        llm_config['endpoint'] = llm_config['api_url']

    # Create instance then initialize with config
    self.llm_interface = LocalLLMInterface()  # ← HARDCODED
    self.llm_interface.initialize(llm_config)
```

**New Code (CORRECT)**:
```python
def _initialize_llm(self) -> None:
    """Initialize LLM interface from registry."""
    llm_type = self.config.get('llm.type', 'ollama')  # Default to ollama
    llm_config = self.config.get('llm', {})

    # Map api_url to endpoint for backward compatibility
    if 'api_url' in llm_config and 'endpoint' not in llm_config:
        llm_config['endpoint'] = llm_config['api_url']

    # Get LLM class from registry (like agent does)
    try:
        llm_class = LLMRegistry.get(llm_type)
    except PluginNotFoundError as e:
        logger.error(f"LLM type '{llm_type}' not found in registry")
        raise OrchestratorException(
            f"Invalid LLM type: {llm_type}. Available: {LLMRegistry.list()}"
        ) from e

    # Create instance and initialize
    self.llm_interface = llm_class()
    self.llm_interface.initialize(llm_config)
```

**Import Addition** (top of file, near line 28):
```python
from src.plugins.exceptions import PluginNotFoundError
```

**Reference Pattern**: Copy exactly how `_initialize_agent()` uses `AgentRegistry` (lines 371-379)

**Validation**:
- Run existing tests with `llm.type: ollama` in test config
- Verify orchestrator initializes without errors
- Verify LLM generates responses correctly

**Success Criteria**:
- ✅ Orchestrator initializes with `llm.type: ollama`
- ✅ All existing tests pass (no behavior change)
- ✅ Error message shown if invalid `llm.type` specified
- ✅ Registry pattern matches agent pattern exactly

---

### PHASE 3: Create OpenAI Codex CLI LLM Plugin (4-5 hours)

**Objective**: Implement `OpenAICodexLLMPlugin` that conforms to `LLMPlugin` interface using CLI subprocess execution

**Files to Create**:
1. `src/llm/openai_codex_interface.py` (new file, ~350 lines)

**Implementation Approach**: CLI-based (subprocess execution), NOT HTTP API
- Similar pattern to `ClaudeCodeLocalAgent` (subprocess execution)
- Uses `subprocess.run(['codex', prompt])` with stdout parsing
- Flat fee subscription model (not pay-per-token API)

**Implementation Guidelines**:

#### Required Interface Methods

From `src/plugins/base.py:265-443`, implement ALL abstract methods:

1. **`initialize(config: Dict[str, Any]) -> None`**
   - Extract `codex_command` from config (default: `'codex'`)
   - Extract `timeout` from config (default: 120 seconds)
   - Verify `codex` CLI is installed and accessible via `which codex` or similar
   - Verify CLI is authenticated (test with simple command)
   - Initialize `RetryManager` using `create_retry_manager_from_config(config)` (M9 pattern)
   - Log initialization success with CLI command path

2. **`generate(prompt: str, **kwargs) -> str`**
   - Build command: `['codex', 'exec', '--full-auto', '--quiet', prompt]` (headless execution mode)
   - Add model: `['codex', 'exec', '--model', model_name, '--full-auto', '--quiet', prompt]`
   - Note: Temperature/max_tokens configured in `~/.codex/config.toml` or via `-c` flag
   - Execute via `subprocess.run()` with:
     - `stdout=subprocess.PIPE`
     - `stderr=subprocess.PIPE`
     - `timeout=self.timeout`
     - `text=True`
   - Call with retry via `self.retry_manager.execute()`
   - Parse stdout for response text
   - Extract token count from stdout/stderr if available
   - Update metrics: calls, total_tokens (estimated), total_latency_ms
   - Handle exceptions:
     - `subprocess.TimeoutExpired` → `LLMTimeoutException`
     - `FileNotFoundError` → `LLMConnectionException` (CLI not installed)
     - Non-zero returncode → `LLMException` with stderr
   - Return response text (stripped of any CLI metadata)

3. **`generate_stream(prompt: str, **kwargs) -> Iterator[str]`**
   - Use `subprocess.Popen()` for streaming output
   - Read stdout line-by-line: `for line in process.stdout: yield line`
   - Handle stream interruption gracefully
   - Update metrics on stream completion
   - Note: May not be supported by all CLI tools (implement best-effort)

4. **`estimate_tokens(text: str) -> int`**
   - Use `tiktoken` if available: `tiktoken.encoding_for_model('gpt-4').encode(text)`
   - Return `len(encoded_tokens)`
   - Fallback if tiktoken unavailable: `len(text) // 4` (rough approximation)
   - Note: Codex may use similar tokenization to GPT models

5. **`is_available() -> bool`**
   - Quick health check: attempt `subprocess.run(['codex', '--version'], timeout=5)`
   - Return `True` if returncode == 0, `False` if any exception
   - Should complete in <1 second
   - Note: Exit code 2 indicates auth failure (not available)
   - Exit code 0 indicates CLI is working and authenticated

6. **`get_model_info() -> Dict[str, Any]`** (optional, but recommended)
   - Return dict with:
     - `model_name`: 'codex'
     - `context_length`: 8192 (typical for Codex)
     - `provider`: 'openai-codex'
     - `type`: 'cli'
     - `execution_mode`: 'subprocess'

#### Configuration Structure

**Default Config**:
```python
DEFAULT_CONFIG = {
    'codex_command': 'codex',  # CLI command name
    'model': 'codex-mini-latest',  # Default model (or gpt-5-codex, o3, etc.)
    'approval_mode': 'full-auto',  # Automation level: suggest, auto-edit, full-auto
    'quiet_mode': True,  # Use --quiet for JSON output
    'timeout': 120,  # Longer timeout for CLI execution
    'retry_attempts': 3,
    'retry_backoff_base': 2.0,
    'retry_backoff_max': 60.0,
}
```

**Required Config Keys**:
- `codex_command`: Command to execute (default: 'codex')
  - May need full path: '/usr/local/bin/codex'
  - Check with `which codex` during initialization

**Optional Config Keys**:
- `model`: Model to use (default: 'codex-mini-latest', options: gpt-5-codex, o3, gpt-5, o4-mini)
- `approval_mode`: Automation level (default: 'full-auto', options: suggest, auto-edit, full-auto)
- `quiet_mode`: JSON output mode (default: True)
- `timeout`: Subprocess timeout in seconds (default: 120)
- `retry_attempts`: Number of retry attempts (default: 3)

**Authentication**:
- OAuth: `codex --login` (browser-based, for ChatGPT Plus/Pro accounts)
- API Key: `OPENAI_API_KEY` environment variable
- Assumes CLI is already authenticated (check during initialization with `codex --version`)

#### Metrics Tracking

Match `LocalLLMInterface` metrics structure exactly:
```python
self.metrics = {
    'calls': 0,
    'total_tokens': 0,
    'total_latency_ms': 0.0,
    'errors': 0,
    'timeouts': 0
}
```

Update after each call:
- `calls`: Increment by 1
- `total_tokens`: Add `response.usage.total_tokens` if available
- `total_latency_ms`: Add elapsed time in milliseconds
- `errors`: Increment on exception
- `timeouts`: Increment on timeout exception

#### Retry Logic Integration

Use M9 `RetryManager` exactly like `LocalLLMInterface` does:

```python
from src.utils.retry_manager import RetryManager, create_retry_manager_from_config

# In initialize():
self.retry_manager = create_retry_manager_from_config(self.config)

# In generate():
def _call():
    return openai.ChatCompletion.create(...)

response = self.retry_manager.execute(_call)
```

**Retryable Errors**:
- `subprocess.TimeoutExpired` (CLI took too long)
- Non-zero returncode with transient error messages (network issues, etc.)
- `OSError` / `IOError` (temporary file system issues)

**Non-Retryable Errors**:
- `FileNotFoundError` (CLI not installed - permanent failure)
- Non-zero returncode with permanent error messages (invalid prompt format, etc.)

#### Error Handling

**Pattern to Follow**:
```python
try:
    # Build command with model and approval mode
    cmd = ['codex', 'exec', '--full-auto', '--quiet']
    if self.model:
        cmd.extend(['--model', self.model])
    cmd.append(prompt)

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=self.timeout,
        text=True,
        check=False  # Don't raise on non-zero returncode, handle manually
    )

    if result.returncode != 0:
        self.metrics['errors'] += 1
        error_msg = result.stderr or "Unknown error"
        logger.error(f"Codex CLI failed (code {result.returncode}): {error_msg}")
        raise LLMException(f"Codex CLI error: {error_msg}")

    response = result.stdout.strip()
    return response

except subprocess.TimeoutExpired as e:
    self.metrics['timeouts'] += 1
    logger.error(f"Codex CLI timeout after {self.timeout}s")
    raise LLMTimeoutException(f"CLI timed out after {self.timeout}s") from e
except FileNotFoundError as e:
    self.metrics['errors'] += 1
    logger.error(f"Codex CLI not found: {self.codex_command}")
    raise LLMConnectionException(
        f"Codex CLI not installed at: {self.codex_command}"
    ) from e
except Exception as e:
    self.metrics['errors'] += 1
    logger.error(f"Codex CLI unexpected error: {e}")
    raise LLMException(f"Unexpected CLI error: {e}") from e
```

#### Logging Guidelines

Use same logging pattern as `LocalLLMInterface`:
- `logger.info()`: Initialization success, significant events
- `logger.debug()`: Per-request details (latency, tokens)
- `logger.warning()`: Rate limits, retries
- `logger.error()`: Errors, failures

**Example**:
```python
logger.info(f"Initialized OpenAICodexLLMPlugin: command={self.codex_command}")
logger.debug(f"Codex CLI generation: {elapsed_ms:.0f}ms")
logger.warning(f"CLI timeout, retrying in {delay}s...")
logger.error(f"Codex CLI not found: {self.codex_command}")
```

#### Reference Implementations

**Copy patterns from**:

**For CLI execution**: `src/agents/claude_code_local.py`
- Subprocess execution pattern (headless mode)
- Stdout/stderr parsing
- Timeout handling
- Command building

**For LLM interface**: `src/llm/local_interface.py`
- Metrics tracking (lines 93-101)
- Retry manager integration (lines 89-90, 160-162)
- Configuration merging (lines 140-162)
- Logging style (lines 173-175, 264-265)

**Template Structure**:
```python
"""OpenAI Codex CLI LLM interface for remote orchestrator.

Implements LLMPlugin interface for OpenAI Codex CLI (flat fee subscription),
enabling CLI-based remote LLM orchestration as alternative to local Qwen/Ollama.
"""

import os
import subprocess
import time
import logging
import shutil
from typing import Dict, Any, Iterator, Optional

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from src.plugins.base import LLMPlugin
from src.plugins.registry import register_llm
from src.plugins.exceptions import (
    LLMException,
    LLMConnectionException,
    LLMTimeoutException,
    LLMResponseException
)
from src.utils.retry_manager import RetryManager, create_retry_manager_from_config

logger = logging.getLogger(__name__)


@register_llm('openai-codex')
class OpenAICodexLLMPlugin(LLMPlugin):
    """OpenAI Codex CLI interface for remote LLM orchestration.

    Provides CLI-based LLM capabilities via OpenAI Codex CLI (flat fee subscription)
    as alternative to local Qwen/Ollama or HTTP API-based providers.

    Example:
        >>> llm = OpenAICodexLLMPlugin()
        >>> llm.initialize({
        ...     'codex_command': 'codex',
        ...     'temperature': 0.7,
        ...     'timeout': 120
        ... })
        >>> response = llm.generate("Validate this code output...")

    Thread-safety: This class is thread-safe. Multiple threads can call
    methods simultaneously.

    Note: Assumes Codex CLI is already installed and authenticated (similar
    to Claude Code CLI authentication pattern).
    """

    DEFAULT_CONFIG = {
        # ... config defaults
    }

    def __init__(self):
        """Initialize OpenAI LLM interface."""
        # ... instance variables

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize OpenAI client with configuration."""
        # ... implementation

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        # ... implementation

    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """Generate with streaming output."""
        # ... implementation

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken."""
        # ... implementation

    def is_available(self) -> bool:
        """Check if OpenAI API is accessible."""
        # ... implementation

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        # ... implementation
```

**Validation**:
- Import in Python REPL: `from src.llm.openai_codex_interface import OpenAICodexLLMPlugin`
- Check registration: `'openai-codex' in LLMRegistry.list()`
- Initialize with default config (assumes CLI installed)
- Generate simple response: "Say hello"
- Verify metrics updated

**Success Criteria**:
- ✅ All 5 abstract methods implemented
- ✅ Registered as `'openai-codex'` in LLMRegistry
- ✅ Imports without errors
- ✅ Initializes when CLI installed
- ✅ Generates responses correctly via subprocess
- ✅ Raises `LLMConnectionException` if CLI not installed
- ✅ Raises `LLMTimeoutException` on timeout
- ✅ Raises `LLMException` on CLI errors
- ✅ Retry logic works (test with transient errors)
- ✅ Metrics tracked correctly
- ✅ Logging output matches pattern

---

### PHASE 4: Configuration Updates (30 minutes)

**Objective**: Document both LLM options in configuration files

**Files to Modify**:
1. `config/config.yaml`
2. `config/default_config.yaml`

**Changes Required**:

**File: `config/default_config.yaml` (lines 5-13)**

**Current**:
```yaml
# Local LLM Configuration (Ollama)
llm:
  type: ollama  # LLM provider type (matches LLMRegistry)
  model: qwen2.5-coder:32b  # Model to use
  api_url: http://172.29.144.1:11434  # Ollama API endpoint
  temperature: 0.7  # Generation temperature (0.0-2.0)
  timeout: 30  # Timeout for generation (seconds)
  max_tokens: 4096  # Maximum tokens to generate
  context_length: 32768  # Model context window size
```

**New**:
```yaml
# LLM Configuration (Orchestrator)
# Two options: local (ollama) or remote (openai)

# OPTION A: Local LLM (Ollama with Qwen) - Hardware deployment
llm:
  type: ollama  # LLM provider type (matches LLMRegistry)
  model: qwen2.5-coder:32b  # Model to use
  api_url: http://172.29.144.1:11434  # Ollama API endpoint
  temperature: 0.7  # Generation temperature (0.0-2.0)
  timeout: 30  # Timeout for generation (seconds)
  max_tokens: 4096  # Maximum tokens to generate
  context_length: 32768  # Model context window size

# OPTION B: Remote LLM (OpenAI Codex CLI) - Subscription or API key deployment
# Uncomment and configure to use:
# llm:
#   type: openai-codex  # LLM provider type (matches LLMRegistry)
#   codex_command: codex  # CLI command (or full path: /usr/local/bin/codex)
#   model: codex-mini-latest  # Model: codex-mini-latest, gpt-5-codex, o3, gpt-5, o4-mini
#   approval_mode: full-auto  # Automation: suggest, auto-edit, full-auto
#   quiet_mode: true  # Use --quiet for JSON output
#   timeout: 120  # Timeout for CLI subprocess (seconds)
#   retry_attempts: 3  # Number of retry attempts on failure
#   # Authentication: OPENAI_API_KEY env var or `codex --login` (OAuth)
```

**File: `config/config.yaml`**

Update comment at top to mention flexible LLM:
```yaml
# Configuration for Claude Code Orchestrator
# Supports both local LLM (Ollama) and remote LLM (OpenAI) orchestration
# See config/default_config.yaml for all options
```

**Validation**:
- Load config with `type: ollama` → works
- Load config with `type: openai-codex` + CLI installed → works
- Load config with invalid `type` → error message shows available types

**Success Criteria**:
- ✅ Both options documented clearly
- ✅ Comments explain use cases (hardware vs subscription)
- ✅ Environment variable pattern shown for API key
- ✅ Default config uses ollama (backward compatible)

---

### PHASE 5: Unit Tests (2 hours)

**Objective**: Test OpenAILLMPlugin in isolation with mocked API calls

**Files to Create**:
1. `tests/test_openai_codex_interface.py` (new file, ~200 lines)

**Test Cases Required**:

#### Test 1: Initialization Success
```python
def test_codex_initialization_success(mock_which_codex):
    """Test successful initialization with Codex CLI installed."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': 'codex', 'temperature': 0.5})

    assert llm.codex_command == 'codex'
    assert llm.temperature == 0.5
```

#### Test 2: Initialization CLI Not Found
```python
def test_codex_initialization_cli_not_found(monkeypatch):
    """Test initialization fails when CLI not installed."""
    monkeypatch.setattr('shutil.which', lambda x: None)

    llm = OpenAICodexLLMPlugin()
    with pytest.raises(LLMConnectionException, match="not installed"):
        llm.initialize({'codex_command': 'codex'})
```

#### Test 3: Generate Success
```python
def test_codex_generate_success(mock_subprocess_success):
    """Test successful generation via CLI."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': 'codex'})

    response = llm.generate("Test prompt")

    assert response == "Mocked CLI response"
    assert llm.metrics['calls'] == 1
```

#### Test 4: Generate CLI Error
```python
def test_codex_generate_cli_error(mock_subprocess_error):
    """Test CLI error handling."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': 'codex'})

    with pytest.raises(LLMException, match="CLI error"):
        llm.generate("Test prompt")

    assert llm.metrics['errors'] > 0
```

#### Test 5: Generate Timeout
```python
def test_codex_generate_timeout(mock_subprocess_timeout):
    """Test timeout handling."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': 'codex', 'timeout': 1})

    with pytest.raises(LLMTimeoutException):
        llm.generate("Test prompt")

    assert llm.metrics['timeouts'] > 0
```

#### Test 6: Token Estimation
```python
def test_codex_estimate_tokens():
    """Test token estimation."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': 'codex'})

    tokens = llm.estimate_tokens("Hello world")
    assert tokens > 0
    assert tokens < 10  # Should be 2-3 tokens
```

#### Test 7: Availability Check
```python
def test_codex_is_available(mock_subprocess_version):
    """Test availability check."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': 'codex'})

    assert llm.is_available() is True
```

#### Test 8: Model Info
```python
def test_codex_get_model_info():
    """Test model info retrieval."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': 'codex'})

    info = llm.get_model_info()
    assert info['model_name'] == 'codex'
    assert info['provider'] == 'openai-codex'
    assert info['type'] == 'cli'
```

#### Test 9: Registry Registration
```python
def test_codex_registered_in_registry():
    """Test OpenAI Codex plugin is registered."""
    from src.llm.openai_codex_interface import OpenAICodexLLMPlugin

    assert 'openai-codex' in LLMRegistry.list()
    llm_class = LLMRegistry.get('openai-codex')
    assert llm_class is OpenAICodexLLMPlugin
```

#### Test 10: CLI Command Customization
```python
def test_codex_custom_command_path():
    """Test custom CLI command path."""
    llm = OpenAICodexLLMPlugin()
    llm.initialize({'codex_command': '/usr/local/bin/codex'})

    assert llm.codex_command == '/usr/local/bin/codex'
```

**Mocking Strategy**:

Use `unittest.mock` to mock subprocess calls:
```python
@pytest.fixture
def mock_subprocess_success(monkeypatch):
    """Mock successful CLI execution."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Mocked CLI response"
    mock_result.stderr = ""

    def mock_run(*args, **kwargs):
        return mock_result

    monkeypatch.setattr('subprocess.run', mock_run)
    return mock_result

@pytest.fixture
def mock_subprocess_timeout(monkeypatch):
    """Mock CLI timeout."""
    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired('codex', 1)

    monkeypatch.setattr('subprocess.run', mock_run)
```

**Test Organization**:
```python
# tests/test_openai_codex_interface.py
import pytest
import subprocess
from unittest.mock import MagicMock, patch

from src.llm.openai_codex_interface import OpenAICodexLLMPlugin
from src.plugins.registry import LLMRegistry
from src.plugins.exceptions import (
    LLMException,
    LLMConnectionException,
    LLMTimeoutException
)

class TestOpenAICodexLLMPlugin:
    """Test suite for OpenAICodexLLMPlugin."""

    def test_initialization_success(self, mock_which_codex):
        # ... test implementation

    def test_initialization_cli_not_found(self, monkeypatch):
        # ... test implementation

    # ... more tests
```

**Validation**:
- Run `pytest tests/test_openai_codex_interface.py -v`
- All tests pass
- Coverage report shows >90% coverage for `src/llm/openai_codex_interface.py`

**Success Criteria**:
- ✅ 10+ test cases covering all major functionality
- ✅ All tests pass
- ✅ Mocking used (no real CLI calls)
- ✅ Error cases tested (CLI not found, timeout, CLI errors)
- ✅ Registry registration tested
- ✅ Metrics tracking tested
- ✅ >90% code coverage for OpenAICodexLLMPlugin

---

### PHASE 6: Integration Tests (1 hour)

**Objective**: Test end-to-end orchestration with OpenAI LLM

**Files to Create**:
1. `tests/test_integration_flexible_llm.py` (new file, ~150 lines)

**Test Cases Required**:

#### Test 1: Orchestrator with Ollama LLM
```python
def test_orchestrator_with_ollama_llm(test_config):
    """Test orchestrator uses Ollama LLM when configured."""
    test_config.set('llm.type', 'ollama')

    orchestrator = Orchestrator(config=test_config)
    orchestrator.initialize()

    assert isinstance(orchestrator.llm_interface, LocalLLMInterface)
    assert orchestrator.llm_interface.model == 'qwen2.5-coder:32b'
```

#### Test 2: Orchestrator with OpenAI Codex LLM
```python
def test_orchestrator_with_codex_llm(test_config, mock_which_codex):
    """Test orchestrator uses OpenAI Codex LLM when configured."""
    test_config.set('llm.type', 'openai-codex')
    test_config.set('llm.codex_command', 'codex')

    orchestrator = Orchestrator(config=test_config)
    orchestrator.initialize()

    assert isinstance(orchestrator.llm_interface, OpenAICodexLLMPlugin)
    assert orchestrator.llm_interface.codex_command == 'codex'
```

#### Test 3: Invalid LLM Type Error
```python
def test_orchestrator_invalid_llm_type(test_config):
    """Test orchestrator raises error for invalid LLM type."""
    test_config.set('llm.type', 'invalid-llm')

    orchestrator = Orchestrator(config=test_config)
    with pytest.raises(OrchestratorException, match="Invalid LLM type"):
        orchestrator.initialize()
```

#### Test 4: Quality Controller with OpenAI Codex
```python
def test_quality_controller_with_codex(test_config, mock_subprocess_success):
    """Test QualityController uses OpenAI Codex LLM correctly."""
    test_config.set('llm.type', 'openai-codex')

    orchestrator = Orchestrator(config=test_config)
    orchestrator.initialize()

    # Mock agent response
    agent_response = "Code implementation here..."

    # Quality controller should use Codex
    quality_result = orchestrator.quality_controller.check_quality(
        response=agent_response,
        task_description="Implement function"
    )

    assert quality_result['quality_score'] > 0.0
    assert orchestrator.llm_interface.metrics['calls'] > 0
```

#### Test 5: Confidence Scorer with OpenAI Codex
```python
def test_confidence_scorer_with_codex(test_config, mock_subprocess_success):
    """Test ConfidenceScorer uses OpenAI Codex LLM correctly."""
    test_config.set('llm.type', 'openai-codex')

    orchestrator = Orchestrator(config=test_config)
    orchestrator.initialize()

    # Mock validation results
    validation_result = {'valid': True, 'complete': True}
    quality_result = {'quality_score': 0.85}

    # Confidence scorer should use Codex
    confidence = orchestrator.confidence_scorer.calculate_confidence(
        validation=validation_result,
        quality=quality_result,
        context={}
    )

    assert 0.0 <= confidence <= 1.0
    assert orchestrator.llm_interface.metrics['calls'] > 0
```

#### Test 6: Switch Between LLMs
```python
def test_switch_between_llms(test_config, mock_which_codex):
    """Test switching LLM type requires new orchestrator instance."""
    # Start with Ollama
    test_config.set('llm.type', 'ollama')
    orch1 = Orchestrator(config=test_config)
    orch1.initialize()
    assert isinstance(orch1.llm_interface, LocalLLMInterface)

    # Switch to OpenAI Codex (new instance)
    test_config.set('llm.type', 'openai-codex')
    orch2 = Orchestrator(config=test_config)
    orch2.initialize()
    assert isinstance(orch2.llm_interface, OpenAICodexLLMPlugin)
```

**Validation**:
- Run `pytest tests/test_integration_flexible_llm.py -v`
- All tests pass
- Both LLM types work correctly with orchestrator

**Success Criteria**:
- ✅ 6+ integration test cases
- ✅ All tests pass
- ✅ Orchestrator works with both ollama and openai-codex types
- ✅ Quality controller uses correct LLM
- ✅ Confidence scorer uses correct LLM
- ✅ Error handling works (invalid type)
- ✅ No changes required to orchestration logic

---

### PHASE 7: Documentation Updates (30 minutes)

**Objective**: Update documentation to reflect flexible LLM support

**Files to Modify**:
1. `docs/design/OBRA_SYSTEM_OVERVIEW.md`
2. `docs/business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md`
3. `CLAUDE.md`

**Changes Required**:

**File: `docs/design/OBRA_SYSTEM_OVERVIEW.md`**

**Section: "Deployment Architecture" (around line 20)**

Update to show both deployment options:
```markdown
### Deployment Architecture

**Two Orchestrator Deployment Options:**

**Option A: Local LLM (Hardware)**
```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (Windows 11 Pro)                               │
│  Ollama + Qwen (RTX 5090, GPU) ← HTTP API                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Hyper-V VM → WSL2                                     │  │
│  │   Obra ─┬─→ subprocess → Claude Code (Local)         │  │
│  │         └─→ HTTP API → Ollama (Validation)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Option B: Remote LLM (Subscription)**
```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (Windows 11 Pro or WSL2)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Obra ─┬─→ subprocess → Claude Code (Local)           │  │
│  │       └─→ HTTPS API → OpenAI (Validation)            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Difference**: Remote LLM requires no GPU, lower hardware requirements.
```

**File: `CLAUDE.md`**

**Section: "Quick Context Refresh" (around line 28)**

Add reference to flexible LLM strategy:
```markdown
### Key References
- **Documentation Index**: `docs/README.md` - Browse all docs
- **ADRs**: `docs/decisions/` - Architecture decisions (12 ADRs)
- **Phase Reports**: `docs/development/phase-reports/` - Latest work summaries
- **Configuration**: `docs/guides/CONFIGURATION_PROFILES_GUIDE.md`
- **Interactive Mode**: `docs/development/INTERACTIVE_STREAMING_QUICKREF.md`
- **Flexible LLM**: `docs/business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md` - Dual deployment model
```

**Validation**:
- Documentation renders correctly
- Architecture diagrams accurate
- References work (no broken links)

**Success Criteria**:
- ✅ Both deployment options documented
- ✅ Architecture diagrams updated
- ✅ References added to key docs
- ✅ No broken links

---

## Testing Strategy

### Unit Test Coverage Requirements
- `src/llm/openai_interface.py`: ≥90% coverage
- `src/orchestrator.py` (modified sections): 100% coverage
- All abstract methods tested
- All error paths tested

### Integration Test Requirements
- Orchestrator initializes with both LLM types
- Quality controller works with both LLM types
- Confidence scorer works with both LLM types
- Invalid LLM type raises clear error
- Config switching works correctly

### Manual Testing Checklist
- [ ] Load config with `llm.type: ollama` → orchestrator works
- [ ] Load config with `llm.type: openai` + API key → orchestrator works
- [ ] Load config with invalid `llm.type` → error message lists available types
- [ ] Generate validation with OpenAI → response received
- [ ] Check metrics after OpenAI call → metrics updated
- [ ] Trigger rate limit → retry logic works
- [ ] Remove API key → initialization fails with clear message
- [ ] Run full orchestration with OpenAI → task completes

---

## Success Criteria

### Functional Requirements
- ✅ LocalLLMInterface registered as 'ollama' in LLMRegistry
- ✅ OpenAILLMPlugin registered as 'openai' in LLMRegistry
- ✅ Orchestrator uses LLMRegistry.get() instead of hardcoding
- ✅ Config with `llm.type: ollama` loads LocalLLMInterface
- ✅ Config with `llm.type: openai` loads OpenAILLMPlugin
- ✅ Invalid `llm.type` raises clear error with available types
- ✅ OpenAI API calls work (generate, estimate_tokens, is_available)
- ✅ Retry logic handles rate limits and timeouts
- ✅ Metrics tracked (calls, tokens, latency, errors)

### Non-Functional Requirements
- ✅ 100% backward compatibility (existing Ollama configs work unchanged)
- ✅ Zero changes to orchestration logic (QualityController, etc.)
- ✅ All existing tests still pass
- ✅ New tests achieve ≥90% coverage on new code
- ✅ Documentation updated with both deployment options
- ✅ Configuration examples clear and complete

### Performance Requirements
- ✅ OpenAI API calls complete in <10 seconds (normal conditions)
- ✅ Retry logic doesn't exceed 60 seconds total (with backoff)
- ✅ No memory leaks from OpenAI client
- ✅ Thread-safe for concurrent requests

---

## Common Pitfalls to Avoid

### Pitfall 1: Not Using Registry
**WRONG**:
```python
if llm_type == 'ollama':
    self.llm_interface = LocalLLMInterface()
elif llm_type == 'openai':
    self.llm_interface = OpenAILLMPlugin()
```

**CORRECT**:
```python
llm_class = LLMRegistry.get(llm_type)
self.llm_interface = llm_class()
```

### Pitfall 2: Forgetting to Register Plugin
**Must have** `@register_llm('openai')` decorator on class definition.
If missing, registry lookup will fail.

### Pitfall 3: Not Matching Interface Exactly
All abstract methods from `LLMPlugin` must be implemented with exact signatures.
Check `src/plugins/base.py:265-443` for requirements.

### Pitfall 4: Hardcoding API Key
Use environment variable pattern:
```python
api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
```
Never log or expose API key in error messages.

### Pitfall 5: Not Handling Rate Limits
OpenAI rate limits are common. Must use retry logic with exponential backoff.
Use existing `RetryManager` from M9.

### Pitfall 6: Inconsistent Metrics
Match `LocalLLMInterface` metrics structure exactly. Components may depend on specific metric keys.

### Pitfall 7: Missing Error Context
When raising exceptions, include context:
```python
raise LLMConnectionException(
    f"Failed to connect to OpenAI at {self.base_url}: {error}"
)
```

### Pitfall 8: Not Testing Without API Key
Must test initialization failure when API key missing. This is common user error.

---

## Validation Checkpoints

### Checkpoint 1: After Phase 1 (Registry)
- [ ] `'ollama'` in `LLMRegistry.list()`
- [ ] `LLMRegistry.get('ollama')` returns `LocalLLMInterface`
- [ ] Existing tests still pass

### Checkpoint 2: After Phase 2 (Orchestrator)
- [ ] Orchestrator initializes with `llm.type: ollama`
- [ ] Orchestrator uses registry (not hardcoded)
- [ ] Invalid `llm.type` raises clear error
- [ ] All existing tests still pass

### Checkpoint 3: After Phase 3 (OpenAI Plugin)
- [ ] `'openai'` in `LLMRegistry.list()`
- [ ] OpenAILLMPlugin imports without errors
- [ ] Can initialize with API key
- [ ] Can generate response
- [ ] Metrics updated correctly

### Checkpoint 4: After Phase 5 (Unit Tests)
- [ ] All unit tests pass
- [ ] ≥90% coverage on OpenAILLMPlugin
- [ ] Error cases tested
- [ ] Registry tested

### Checkpoint 5: After Phase 6 (Integration Tests)
- [ ] Orchestrator works with both LLM types
- [ ] Quality controller uses correct LLM
- [ ] Confidence scorer uses correct LLM
- [ ] All integration tests pass

### Checkpoint 6: Final Validation
- [ ] All tests pass (unit + integration)
- [ ] Documentation updated
- [ ] Configuration examples work
- [ ] Manual testing checklist complete
- [ ] No regressions in existing functionality

---

## Implementation Order

Execute phases in strict sequence:

1. **PHASE 1** (20 min) - Register LocalLLMInterface
   - Quick win, validates registry approach

2. **PHASE 2** (30 min) - Update Orchestrator
   - Core architectural change, must work before proceeding

3. **PHASE 3** (4 hours) - Implement OpenAI Plugin
   - Main implementation work

4. **PHASE 4** (30 min) - Update Configuration
   - Documentation/usability

5. **PHASE 5** (2 hours) - Unit Tests
   - Validate OpenAI plugin in isolation

6. **PHASE 6** (1 hour) - Integration Tests
   - Validate end-to-end with orchestrator

7. **PHASE 7** (30 min) - Documentation
   - Final polish

**Total**: ~8.5 hours

---

## File Checklist

### Files to Modify
- [ ] `src/llm/local_interface.py` - Add `@register_llm('ollama')`
- [ ] `src/orchestrator.py` - Update `_initialize_llm()` to use registry
- [ ] `config/config.yaml` - Add OpenAI option
- [ ] `config/default_config.yaml` - Add OpenAI option
- [ ] `docs/design/OBRA_SYSTEM_OVERVIEW.md` - Update deployment options
- [ ] `CLAUDE.md` - Add flexible LLM reference

### Files to Create
- [ ] `src/llm/openai_codex_interface.py` - New OpenAI Codex CLI plugin (~350 lines)
- [ ] `tests/test_openai_codex_interface.py` - Unit tests (~200 lines)
- [ ] `tests/test_integration_flexible_llm.py` - Integration tests (~150 lines)

### Total New Code
- **Production**: ~350 lines
- **Tests**: ~350 lines
- **Config/Docs**: ~100 lines modifications
- **Grand Total**: ~800 lines

---

## Dependencies

### System Requirements
- **OpenAI Codex CLI** - Must be installed and accessible in PATH
  - Install: `brew install --cask codex` (macOS) or `npm install -g @openai/codex` (cross-platform)
  - Verify with: `which codex` or `codex --version`
  - Authenticate: `codex --login` (OAuth) or set `OPENAI_API_KEY` environment variable
  - Works with ChatGPT Plus/Pro or OpenAI API key

### Python Packages Required
- `tiktoken` - Token estimation (optional but recommended)

**Update `requirements.txt`**:
```
tiktoken>=0.5.0  # Optional but recommended for token estimation
```

**Note**: No `openai` package needed for CLI-based approach. This uses subprocess execution, not HTTP API.

### Environment Variables
- None required (CLI-based authentication, not API key-based)

### Existing Dependencies (Already Available)
- `src.plugins.base.LLMPlugin` - Abstract interface
- `src.plugins.registry.LLMRegistry` - Plugin registry
- `src.utils.retry_manager.RetryManager` - Retry logic (M9)
- `src.plugins.exceptions` - Exception classes

---

## Post-Implementation Validation

### Smoke Test Script

Create `scripts/test_flexible_llm.py`:
```python
"""Smoke test for flexible LLM orchestrator."""

import os
from src.core.config import Config
from src.orchestrator import Orchestrator

def test_ollama_llm():
    """Test with Ollama LLM."""
    print("Testing Ollama LLM...")
    config = Config.load('config/config.yaml')
    config.set('llm.type', 'ollama')

    orch = Orchestrator(config=config)
    orch.initialize()

    assert orch.llm_interface.__class__.__name__ == 'LocalLLMInterface'
    print("✓ Ollama LLM works")

def test_openai_llm():
    """Test with OpenAI LLM."""
    print("Testing OpenAI LLM...")

    if not os.getenv('OPENAI_API_KEY'):
        print("⚠ Skipping OpenAI test (no API key)")
        return

    config = Config.load('config/config.yaml')
    config.set('llm.type', 'openai')
    config.set('llm.model', 'gpt-4o')

    orch = Orchestrator(config=config)
    orch.initialize()

    assert orch.llm_interface.__class__.__name__ == 'OpenAILLMPlugin'

    # Test generation
    response = orch.llm_interface.generate("Say 'test successful'")
    assert len(response) > 0
    print(f"✓ OpenAI LLM works (response: {response[:50]}...)")

if __name__ == '__main__':
    test_ollama_llm()
    test_openai_llm()
    print("\n✅ All smoke tests passed")
```

**Run**: `python scripts/test_flexible_llm.py`

---

## Rollback Plan

If implementation fails or issues discovered:

### Rollback Step 1: Revert Orchestrator
```python
# src/orchestrator.py:_initialize_llm()
# Revert to:
self.llm_interface = LocalLLMInterface()
self.llm_interface.initialize(llm_config)
```

### Rollback Step 2: Remove OpenAI Plugin
- Delete `src/llm/openai_interface.py`
- Delete `tests/test_openai_interface.py`
- Delete `tests/test_integration_flexible_llm.py`

### Rollback Step 3: Revert Config
- Remove OpenAI sections from config files
- Remove `@register_llm('ollama')` decorator (optional, doesn't hurt)

### Rollback Step 4: Remove Dependencies
- Remove `openai` and `tiktoken` from requirements.txt

**Result**: System returns to pre-implementation state with zero impact.

---

## Timeline Estimate

| Phase | Description | Duration | Start After |
|-------|-------------|----------|-------------|
| 1 | Register LocalLLMInterface | 20 min | Immediate |
| 2 | Update Orchestrator | 30 min | Phase 1 |
| 3 | Create OpenAI Plugin | 4 hours | Phase 2 |
| 4 | Configuration Updates | 30 min | Phase 3 |
| 5 | Unit Tests | 2 hours | Phase 4 |
| 6 | Integration Tests | 1 hour | Phase 5 |
| 7 | Documentation | 30 min | Phase 6 |
| **TOTAL** | **End-to-End** | **~8.5 hours** | - |

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 5 → Phase 6

**Parallelizable**: Phase 4 (config) and Phase 7 (docs) can be done anytime after Phase 3

---

## Status Tracking

Mark completion as you proceed:

- [ ] PHASE 1: Register LocalLLMInterface
- [ ] PHASE 2: Update Orchestrator
- [ ] PHASE 3: Create OpenAI Plugin
- [ ] PHASE 4: Configuration Updates
- [ ] PHASE 5: Unit Tests
- [ ] PHASE 6: Integration Tests
- [ ] PHASE 7: Documentation Updates
- [ ] All Tests Pass
- [ ] Smoke Test Pass
- [ ] Manual Validation Complete

---

**Document Version**: 1.0
**Last Updated**: November 5, 2025
**Status**: Ready for Implementation
**Target**: Claude Code autonomous execution
