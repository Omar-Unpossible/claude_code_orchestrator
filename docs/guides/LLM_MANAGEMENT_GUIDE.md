# LLM Management Guide

**Version**: 1.6.0
**Last Updated**: November 12, 2025
**Status**: Production Ready

## Overview

This guide covers Obra's flexible LLM (Language Model) management system, including:
- Graceful fallback when LLM services are unavailable
- Runtime LLM connection and switching
- Configuration options for local and remote LLMs
- Troubleshooting common LLM issues

## Table of Contents

1. [Quick Start](#quick-start)
2. [Supported LLM Providers](#supported-llm-providers)
3. [Configuration](#configuration)
4. [CLI Commands](#cli-commands)
5. [Programmatic API](#programmatic-api)
6. [Graceful Fallback](#graceful-fallback)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Quick Start

### Scenario 1: Ollama is Down on Startup

```bash
# Obra loads with warning, doesn't crash
$ python -m src.cli init
⚠ Could not connect to LLM service (ollama).
  Obra loaded but you need a working LLM to execute tasks.

# Start Ollama service
$ ollama serve

# Reconnect to LLM
$ python -m src.cli llm reconnect
✓ Successfully connected to LLM: ollama

# Now execute tasks
$ python -m src.cli task execute 1
```

### Scenario 2: Switch from Ollama to OpenAI Codex

```bash
# Check current LLM
$ python -m src.cli llm status
🔌 LLM Connection Status
  Type:     ollama
  Model:    qwen2.5-coder:32b
  Endpoint: http://localhost:11434
✓ Status:   CONNECTED

# Switch to OpenAI Codex
$ python -m src.cli llm switch openai-codex --model gpt-5-codex
🔄 Switching to openai-codex
   Model: gpt-5-codex
✓ Successfully switched to openai-codex

# Verify
$ python -m src.cli llm status
🔌 LLM Connection Status
  Type:     openai-codex
  Model:    gpt-5-codex
✓ Status:   CONNECTED
```

---

## Supported LLM Providers

Obra supports two LLM provider types via the plugin system:

### 1. **Ollama** (Local LLM)
- **Type**: `ollama`
- **Use Case**: Hardware deployment, local GPU inference
- **Requirements**: Ollama service running, GPU (recommended)
- **Models**: Qwen 2.5 Coder, Llama 3, DeepSeek, etc.
- **Endpoint**: HTTP API (default: `http://localhost:11434`)

**Advantages**:
- ✅ No API costs (runs on your hardware)
- ✅ Full data privacy (nothing leaves your machine)
- ✅ No rate limits
- ✅ Fast inference with GPU

**Disadvantages**:
- ❌ Requires powerful GPU (RTX 5090 for 32B models)
- ❌ Initial model download (10-20GB)
- ❌ Must manage Ollama service lifecycle

### 2. **OpenAI Codex** (Remote LLM)
- **Type**: `openai-codex`
- **Use Case**: Cloud deployment, no local GPU
- **Requirements**: OpenAI API key or subscription
- **Models**: GPT-5 Codex, Codex Mini, O3, O4-Mini
- **Interface**: CLI subprocess (similar to Claude Code)

**Advantages**:
- ✅ No hardware requirements
- ✅ Access to latest OpenAI models
- ✅ Managed service (no maintenance)
- ✅ High availability

**Disadvantages**:
- ❌ API costs (pay per token or subscription)
- ❌ Data sent to OpenAI servers
- ❌ Rate limits apply
- ❌ Network dependency

---

## Configuration

### Option 1: Config File (`config/config.yaml`)

**Ollama Configuration**:
```yaml
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434
  temperature: 0.7
  timeout: 30
  max_tokens: 4096
  context_length: 32768
```

**OpenAI Codex Configuration**:
```yaml
llm:
  type: openai-codex
  codex_command: codex  # or /usr/local/bin/codex
  model: gpt-5-codex  # or codex-mini-latest, o3, o4-mini
  full_auto: true
  timeout: 120
  retry_attempts: 3
```

### Option 2: Environment Variables

**Syntax**: `ORCHESTRATOR_{SECTION}_{KEY}=value`

**Ollama via Environment**:
```bash
export ORCHESTRATOR_LLM_TYPE=ollama
export ORCHESTRATOR_LLM_MODEL=qwen2.5-coder:32b
export ORCHESTRATOR_LLM_API_URL=http://localhost:11434
export ORCHESTRATOR_LLM_TEMPERATURE=0.7
```

**OpenAI Codex via Environment**:
```bash
export ORCHESTRATOR_LLM_TYPE=openai-codex
export ORCHESTRATOR_LLM_MODEL=gpt-5-codex
export ORCHESTRATOR_LLM_TIMEOUT=120
export OPENAI_API_KEY=sk-...  # Authentication
```

**Precedence**: Environment variables override config file settings.

### Option 3: Programmatic Configuration

```python
from src.orchestrator import Orchestrator
from src.core.config import Config

config = Config.load()
orchestrator = Orchestrator(config=config)
orchestrator.initialize()

# Reconnect with new configuration
orchestrator.reconnect_llm(
    llm_type='openai-codex',
    llm_config={
        'model': 'gpt-5-codex',
        'timeout': 120
    }
)
```

---

## CLI Commands

### `obra llm status`
Check current LLM connection status.

```bash
$ python -m src.cli llm status

🔌 LLM Connection Status
========================================
  Type:     ollama
  Model:    qwen2.5-coder:32b
  Endpoint: http://localhost:11434

✓ Status:   CONNECTED
✓ LLM is responding and ready to use
```

**Use Cases**:
- Verify LLM is running before executing tasks
- Diagnose connection issues
- Check current configuration

---

### `obra llm list`
List all available LLM providers.

```bash
$ python -m src.cli llm list

📋 Available LLM Providers
========================================
  • ollama               ✓ ACTIVE
  • openai-codex
  • mock

Configuration examples:

  Ollama (local):
    llm.type: ollama
    llm.model: qwen2.5-coder:32b
    llm.api_url: http://localhost:11434

  OpenAI Codex (remote):
    llm.type: openai-codex
    llm.model: gpt-5-codex
    llm.timeout: 120
```

**Use Cases**:
- See which LLM providers are registered
- Get configuration examples
- Verify plugins are loaded correctly

---

### `obra llm reconnect`
Reconnect to LLM or switch providers.

**Syntax**:
```bash
obra llm reconnect [OPTIONS]

Options:
  -t, --type TEXT      LLM type (ollama, openai-codex)
  -m, --model TEXT     Model name
  -e, --endpoint TEXT  API endpoint URL (for Ollama)
  --timeout INTEGER    Timeout in seconds
```

**Examples**:

```bash
# Reconnect to current LLM (after it comes online)
$ obra llm reconnect
🔄 Reconnecting to LLM: ollama
✓ Successfully connected to LLM: ollama

# Switch to OpenAI Codex
$ obra llm reconnect --type openai-codex --model gpt-5-codex
🔄 Switching to LLM: openai-codex
   Configuration: {'model': 'gpt-5-codex'}
✓ Successfully connected to LLM: openai-codex

# Switch to Ollama with specific endpoint
$ obra llm reconnect --type ollama --endpoint http://192.168.1.100:11434
🔄 Switching to LLM: ollama
   Configuration: {'endpoint': 'http://192.168.1.100:11434', ...}
✓ Successfully connected to LLM: ollama

# Change only model (keep current type)
$ obra llm reconnect --model qwen2.5-coder:7b
🔄 Reconnecting to LLM: ollama
   Configuration: {'model': 'qwen2.5-coder:7b'}
✓ Successfully connected to LLM: ollama
```

**Use Cases**:
- Reconnect after LLM service restarts
- Switch between local and remote LLMs
- Change models without editing config files
- Test different LLM configurations

---

### `obra llm switch`
Quick switch between common LLM providers (shortcut for `reconnect`).

**Syntax**:
```bash
obra llm switch {ollama|openai-codex} [OPTIONS]

Options:
  -m, --model TEXT  Model name (optional, uses defaults)
```

**Examples**:

```bash
# Switch to Ollama (default: qwen2.5-coder:32b)
$ obra llm switch ollama
🔄 Switching to ollama
   Model: qwen2.5-coder:32b
✓ Successfully switched to ollama

# Switch to OpenAI Codex (default: gpt-5-codex)
$ obra llm switch openai-codex
🔄 Switching to openai-codex
   Model: gpt-5-codex
✓ Successfully switched to openai-codex

# Switch with specific model
$ obra llm switch openai-codex --model o3
🔄 Switching to openai-codex
   Model: o3
✓ Successfully switched to openai-codex
```

**Use Cases**:
- Quickly toggle between providers during development
- Test behavior differences between LLMs
- Use faster model for testing, production model for deployment

---

## Programmatic API

### `orchestrator.reconnect_llm()`

Reconnect or reconfigure LLM after Obra initialization.

**Signature**:
```python
def reconnect_llm(
    self,
    llm_type: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None
) -> bool
```

**Parameters**:
- `llm_type`: New LLM provider type (e.g., `'ollama'`, `'openai-codex'`). If `None`, uses current config.
- `llm_config`: Dictionary of configuration options. If `None`, uses current config. Merged with existing config.

**Returns**:
- `True` if connection successful
- `False` if connection failed

**Examples**:

```python
# Reconnect to current LLM
success = orchestrator.reconnect_llm()
if not success:
    print("Failed to connect to LLM")

# Switch to OpenAI Codex
success = orchestrator.reconnect_llm(
    llm_type='openai-codex',
    llm_config={'model': 'gpt-5-codex', 'timeout': 120}
)

# Update only specific config values
success = orchestrator.reconnect_llm(
    llm_config={'temperature': 0.3, 'max_tokens': 8192}
)

# Full configuration change
success = orchestrator.reconnect_llm(
    llm_type='ollama',
    llm_config={
        'model': 'qwen2.5-coder:7b',
        'endpoint': 'http://192.168.1.100:11434',
        'temperature': 0.7,
        'timeout': 60
    }
)
```

---

### `orchestrator.check_llm_available()`

Check if LLM is connected and responding.

**Signature**:
```python
def check_llm_available(self) -> bool
```

**Returns**:
- `True` if LLM is ready for use
- `False` if LLM is unavailable or not responding

**Examples**:

```python
# Check before executing task
if orchestrator.check_llm_available():
    result = orchestrator.execute_task(task_id=1)
else:
    print("LLM not available. Reconnecting...")
    if orchestrator.reconnect_llm():
        result = orchestrator.execute_task(task_id=1)
    else:
        print("Failed to connect to LLM")

# Periodic health check
import time
while True:
    if not orchestrator.check_llm_available():
        print("LLM connection lost, attempting reconnect...")
        orchestrator.reconnect_llm()
    time.sleep(60)  # Check every minute
```

---

## Graceful Fallback

**Key Feature**: Obra initializes successfully even if LLM service is unavailable.

### Behavior

**Before (v1.5.0 and earlier)**:
```python
# Ollama is down
orchestrator = Orchestrator()
orchestrator.initialize()  # ❌ CRASH: LLMConnectionException
```

**After (v1.6.0+)**:
```python
# Ollama is down
orchestrator = Orchestrator()
orchestrator.initialize()  # ✓ Succeeds with warning

# Obra is running, but LLM is None
print(orchestrator.llm_interface)  # None

# Attempting to execute task prompts to reconnect
orchestrator.execute_task(1)
# OrchestratorException: LLM service not available
# Recovery: orchestrator.reconnect_llm()

# Reconnect when service comes online
orchestrator.reconnect_llm()  # ✓ Connected
orchestrator.execute_task(1)  # ✓ Executes successfully
```

### Warning Messages

When LLM initialization fails, Obra displays helpful warnings:

```
[OBRA WARNING] ⚠ Could not connect to LLM service (ollama).
                Obra loaded but you need a working LLM to execute tasks.

[OBRA WARNING] To fix: Configure a valid LLM in config/config.yaml or use environment variables:
[OBRA WARNING]   Option 1 (Local): llm.type=ollama, llm.api_url=http://localhost:11434
[OBRA WARNING]   Option 2 (Remote): llm.type=openai-codex, llm.model=gpt-5-codex
[OBRA WARNING] Then reconnect: orchestrator.reconnect_llm()
```

### Use Cases

1. **Development**: Start Obra before starting Ollama service
2. **Debugging**: Obra loads even if LLM configuration is incorrect
3. **Migration**: Switch LLMs without restarting Obra
4. **Resilience**: Temporary network issues don't crash Obra
5. **Testing**: Run Obra without LLM for unit testing

---

## Troubleshooting

### Issue: "LLM service not available"

**Symptoms**:
```bash
$ python -m src.cli llm status
✗ Status:   UNREACHABLE
✗ LLM service is not responding
```

**Solutions**:

1. **Check LLM service is running**:
   ```bash
   # For Ollama
   $ ps aux | grep ollama
   $ ollama serve  # If not running

   # For OpenAI Codex
   $ which codex
   $ codex --version
   ```

2. **Verify endpoint configuration**:
   ```bash
   $ python -m src.cli config show | grep -A 5 'llm:'
   llm:
     type: ollama
     api_url: http://localhost:11434  # Check this
   ```

3. **Test connectivity**:
   ```bash
   # For Ollama
   $ curl http://localhost:11434/api/tags

   # For OpenAI Codex
   $ codex --help
   ```

4. **Reconnect with correct settings**:
   ```bash
   $ python -m src.cli llm reconnect --endpoint http://localhost:11434
   ```

---

### Issue: "LLM type not found in registry"

**Symptoms**:
```bash
[OBRA WARNING] ⚠ LLM type 'invalid-llm' not registered.
                Available: ['ollama', 'openai-codex', 'mock']
```

**Solutions**:

1. **Check available providers**:
   ```bash
   $ python -m src.cli llm list
   ```

2. **Fix configuration**:
   ```bash
   # Update config.yaml
   llm:
     type: ollama  # Must be one of: ollama, openai-codex
   ```

3. **Reconnect with valid type**:
   ```bash
   $ python -m src.cli llm reconnect --type ollama
   ```

---

### Issue: "Model not found"

**Symptoms**:
```
LLMModelNotFoundException: Model 'nonexistent-model' not found
```

**Solutions**:

1. **List available models**:
   ```bash
   # For Ollama
   $ ollama list

   # For OpenAI Codex
   $ codex --list-models  # If supported
   ```

2. **Pull missing model** (Ollama):
   ```bash
   $ ollama pull qwen2.5-coder:32b
   ```

3. **Update configuration**:
   ```bash
   $ python -m src.cli llm reconnect --model qwen2.5-coder:32b
   ```

---

### Issue: Authentication Failure (OpenAI Codex)

**Symptoms**:
```
AuthenticationError: Invalid API key
```

**Solutions**:

1. **Set API key**:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

2. **Or authenticate via CLI**:
   ```bash
   $ codex --login  # OAuth flow
   ```

3. **Verify authentication**:
   ```bash
   $ codex whoami
   ```

---

### Issue: Network Timeouts

**Symptoms**:
```
LLMTimeoutException: Request timed out after 30s
```

**Solutions**:

1. **Increase timeout**:
   ```bash
   $ python -m src.cli llm reconnect --timeout 120
   ```

2. **Check network latency**:
   ```bash
   # For Ollama
   $ ping localhost

   # For OpenAI
   $ ping api.openai.com
   ```

3. **Use local LLM for better latency**:
   ```bash
   $ python -m src.cli llm switch ollama
   ```

---

## Best Practices

### 1. **Always Check LLM Before Critical Operations**

```python
if not orchestrator.check_llm_available():
    logging.error("LLM unavailable, aborting operation")
    orchestrator.reconnect_llm()
    if not orchestrator.check_llm_available():
        raise RuntimeError("Cannot proceed without LLM")

# Proceed with confidence
orchestrator.execute_task(critical_task_id)
```

### 2. **Use Appropriate LLM for Environment**

- **Development/Testing**: Ollama with smaller models (7B) for speed
- **Production**: Ollama with 32B models or OpenAI Codex for quality
- **CI/CD**: Mock LLM for unit tests (no network dependency)
- **Remote deployment**: OpenAI Codex (no GPU required)

### 3. **Handle Reconnection Gracefully**

```python
def execute_with_retry(orchestrator, task_id, max_retries=3):
    for attempt in range(max_retries):
        if not orchestrator.check_llm_available():
            logging.warning(f"LLM unavailable, reconnecting (attempt {attempt+1})")
            if not orchestrator.reconnect_llm():
                time.sleep(2 ** attempt)  # Exponential backoff
                continue

        try:
            return orchestrator.execute_task(task_id)
        except OrchestratorException as e:
            if "LLM" in str(e):
                logging.error("LLM error during execution, retrying...")
                orchestrator.llm_interface = None  # Force reconnect
                continue
            raise

    raise RuntimeError("Failed to execute task after retries")
```

### 4. **Log LLM Changes for Debugging**

```python
import logging

logger = logging.getLogger(__name__)

# Before switching
current_llm = orchestrator.config.get('llm.type')
logger.info(f"Switching from {current_llm} to openai-codex")

# After switching
if orchestrator.reconnect_llm(llm_type='openai-codex'):
    logger.info("Successfully switched to openai-codex")
else:
    logger.error("Failed to switch LLM")
```

### 5. **Use Environment Variables for Deployment**

```bash
# docker-compose.yml
services:
  obra:
    environment:
      - ORCHESTRATOR_LLM_TYPE=openai-codex
      - ORCHESTRATOR_LLM_MODEL=gpt-5-codex
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

### 6. **Monitor LLM Health**

```python
import prometheus_client

llm_availability = prometheus_client.Gauge(
    'obra_llm_available',
    'LLM availability status (1=available, 0=unavailable)'
)

def check_llm_health():
    is_available = orchestrator.check_llm_available()
    llm_availability.set(1 if is_available else 0)
    return is_available

# Run periodically
import schedule
schedule.every(1).minutes.do(check_llm_health)
```

---

## Related Documentation

- **[CLAUDE.md](../../CLAUDE.md)** - LLM Management section
- **[Configuration Guide](CONFIGURATION_PROFILES_GUIDE.md)** - Full configuration reference
- **[Flexible LLM Strategy](../business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md)** - Architecture rationale
- **[Architecture](../architecture/ARCHITECTURE.md)** - Plugin system design

---

**Questions?** Check `obra llm --help` or file an issue at [GitHub Issues](https://github.com/Omar-Unpossible/claude_code_orchestrator/issues).
