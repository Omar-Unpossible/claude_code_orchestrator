# 🎯 How to Start Obra Correctly

## ✅ THE FIX IS COMPLETE

I've fixed the `ParsedIntent` AttributeError bug in `src/interactive.py`. All tests pass.

## 🚀 Quick Start (Use This!)

```bash
cd ~/projects/claude_code_orchestrator
./scripts/startup/obra.sh
```

That's it! The script handles everything automatically.

## 📋 What the Script Does

1. ✅ Activates the virtual environment
2. ✅ Verifies correct Python is being used
3. ✅ Checks Ollama connection
4. ✅ Starts Obra interactive mode

## 🔍 If You See the Codex Error Again

The error you were seeing:
```
ERROR: unexpected status 400 Bad Request: {"detail":"The 'qwen2.5-coder:32b' model is not supported when using Codex with a ChatGPT account."}
```

This happens when you start Obra WITHOUT the virtual environment activated.

### ❌ WRONG WAY (Don't do this):
```bash
python3 -m src.cli interactive  # Uses system Python!
```

### ✅ RIGHT WAY (Do this):
```bash
./scripts/startup/obra.sh  # Uses venv Python automatically
```

## 💡 Why This Matters

Without the virtual environment:
- Python can't find the required dependencies
- LLM plugins fail to register
- Fallback behavior may try to use Codex instead of Ollama
- Everything breaks

With the virtual environment:
- All dependencies are available
- Ollama LLM plugin registers correctly
- Natural language commands work perfectly
- Everything just works

## 🧪 Test It Works

After starting with `./scripts/startup/obra.sh`, try these commands:

```
# Natural language (no slash needed)
list all projects
create an epic for user authentication
show me the open tasks

# System commands (need slash)
/llm status
/help
/status
```

## 📝 Summary of Changes

### Fixed Files:
- `src/interactive.py` - Lines 710-753 updated to handle `ParsedIntent` correctly

### Helper Scripts (in `scripts/` directory):
- `scripts/startup/obra.sh` - Main startup script (USE THIS!)
- `scripts/testing/test_exact_flow.py` - Test script to verify everything works
- `scripts/testing/test_with_logging.py` - Diagnostic script with detailed logging
- See `scripts/README.md` for all available helper scripts

## ❓ Troubleshooting

### Issue: "LLM not available" message
**Solution**: Check if Ollama is running on your host machine

```bash
curl http://10.0.75.1:11434/api/tags
# Should return JSON with model list
```

### Issue: Still seeing Codex errors
**Solution**: Make sure you're using `./scripts/startup/obra.sh` and NOT running Python directly

### Issue: Script says "virtual environment not found"
**Solution**: Create it:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## 🎉 You're All Set!

Just run `./scripts/startup/obra.sh` and start using natural language commands!

For more helper scripts, see `scripts/README.md`.

---

**Last Updated**: November 13, 2025
**Version**: v1.7.2 (Post-Fix)
