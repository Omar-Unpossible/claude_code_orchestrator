# Obra Scripts Directory

This directory contains helper scripts for development, testing, and operations.

## Directory Structure

### 📦 `startup/` - Main Startup Scripts
**Used frequently** - Scripts to launch Obra with proper environment setup.

- **`obra.sh`** - Main startup script (⭐ USE THIS!)
  ```bash
  ./scripts/startup/obra.sh
  ```
  Activates venv, verifies Ollama connection, starts interactive mode

- **`start_obra.sh`** - Alternative startup with auto-setup
  ```bash
  ./scripts/startup/start_obra.sh
  ```
  Creates venv if missing, installs dependencies, starts interactive mode

### 🧪 `testing/` - Test Scripts
**Used frequently** - Integration and manual test scripts.

- **`test_exact_flow.py`** - Test the exact interactive mode flow
  ```bash
  python scripts/testing/test_exact_flow.py
  ```
  Validates LLM initialization and NL command processing

- **`test_with_logging.py`** - Test with detailed logging enabled
  ```bash
  python scripts/testing/test_with_logging.py
  ```

- **`test_llm_config.py`** - Test LLM configuration loading
  ```bash
  python scripts/testing/test_llm_config.py
  ```

- **`test_llm_switching.py`** - Test switching between LLM providers
  ```bash
  python scripts/testing/test_llm_switching.py
  ```

- **`test_codex_no_model.py`** - Test OpenAI Codex without model parameter
  ```bash
  python scripts/testing/test_codex_no_model.py
  ```

### 🔍 `diagnostic/` - Debugging & Troubleshooting
Scripts to diagnose issues and verify configuration.

- **`check_python_env.sh`** - Verify Python environment and LLM plugins
  ```bash
  ./scripts/diagnostic/check_python_env.sh
  ```
  Shows which Python is active, checks venv status, tests LLM imports

- **`diagnose_llm_issue.py`** - Diagnose LLM connection issues
  ```bash
  python scripts/diagnostic/diagnose_llm_issue.py
  ```
  Comprehensive LLM connectivity and configuration diagnostics

- **`debug_interactive_start.py`** - Debug interactive mode startup
  ```bash
  python scripts/diagnostic/debug_interactive_start.py
  ```

- **`run_with_debug_logging.sh`** - Run Obra with debug logging enabled
  ```bash
  ./scripts/diagnostic/run_with_debug_logging.sh
  ```

- **`verify_fix.sh`** - Verify specific bug fixes
  ```bash
  ./scripts/diagnostic/verify_fix.sh
  ```

### 📚 `examples/` - Example Usage Scripts
Example scripts showing how to use Obra programmatically.

- **`run_obra.py`** - Simple example: Send a single task to Obra
  ```bash
  python scripts/examples/run_obra.py
  ```
  Edit the `USER_PROMPT` variable to customize the task

- **`run_obra_iterative.py`** - Advanced example: Multi-iteration orchestration
  ```bash
  python scripts/examples/run_obra_iterative.py
  ```
  Shows quality gating, validation, and iterative improvement

### 🛠️ `utilities/` - Utility Scripts
One-off utilities and migration scripts.

- (Currently empty - utilities are added as needed)

### 📋 `archive/` - Historical Scripts
Archived scripts from previous development phases.

- See `archive/` subdirectories for historical test and development scripts

## Quick Reference

### Most Common Tasks

**Start Obra (interactive mode):**
```bash
cd /home/omarwsl/projects/claude_code_orchestrator
./scripts/startup/obra.sh
```

**Run integration tests:**
```bash
python scripts/testing/test_exact_flow.py
```

**Check environment setup:**
```bash
./scripts/diagnostic/check_python_env.sh
```

**Diagnose LLM issues:**
```bash
python scripts/diagnostic/diagnose_llm_issue.py
```

**Test a simple orchestration:**
```bash
python scripts/examples/run_obra.py
```

## Usage Notes

### Shell Scripts (.sh)
- Run from project root: `./scripts/startup/obra.sh`
- Already executable (chmod +x)
- Most use absolute paths internally, so they work from anywhere

### Python Scripts (.py)
- Can run from project root or with full path
- All scripts add project root to `sys.path` automatically
- No need to activate venv for scripts that don't import Obra modules

### Startup Scripts Best Practices

1. **Always use `obra.sh` for interactive mode** - It handles environment setup automatically
2. **Don't run `python -m src.cli interactive` directly** - Missing venv activation breaks LLM plugins
3. **Check Ollama connection first** if you see LLM errors

## Troubleshooting

### Script says "Permission denied"
Make shell scripts executable:
```bash
chmod +x scripts/startup/*.sh scripts/diagnostic/*.sh
```

### Python import errors
Make sure you're running from the project root:
```bash
cd /home/omarwsl/projects/claude_code_orchestrator
python scripts/testing/test_exact_flow.py
```

### LLM connection issues
1. Check Ollama is running: `curl http://10.0.75.1:11434/api/tags`
2. Run diagnostics: `python scripts/diagnostic/diagnose_llm_issue.py`
3. Verify environment: `./scripts/diagnostic/check_python_env.sh`

---

**Last Updated**: November 13, 2025
**Version**: v1.7.2
