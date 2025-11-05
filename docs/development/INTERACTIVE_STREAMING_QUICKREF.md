# Interactive Streaming - Quick Reference

**Quick Links**:
- 📋 [Full Implementation Plan](INTERACTIVE_STREAMING_IMPLEMENTATION_PLAN.md)
- 📝 [ADR-011](../decisions/ADR-011-interactive-streaming-interface.md)

---

## TL;DR

Add `--stream` and `--interactive` flags to Obra CLI for real-time visibility and control:

```bash
# Real-time streaming (Phase 1)
./venv/bin/python -m src.cli task execute 3 --stream

# Interactive mode with command injection (Phase 2)
./venv/bin/python -m src.cli task execute 3 --stream --interactive
```

**Commands**:
- `/to-claude <message>` - Inject guidance into next prompt
- `/pause` / `/resume` - Pause/resume execution
- `/override-decision RETRY` - Override Obra's decision
- `/status` - Show current metrics

---

## Phase 1: Streaming (1-2 hours)

### Files to Create

```
src/utils/streaming_handler.py    # Custom log handler with colors
```

### Files to Modify

```
src/orchestrator.py    # Add stream parameter
src/cli.py             # Add --stream flag
```

### Key Code Locations

**StreamingHandler** (`src/utils/streaming_handler.py`):
```python
class StreamingHandler(logging.Handler):
    def emit(self, record: LogRecord):
        # Color code based on record content
        if "OBRA→CLAUDE" in record.msg:
            print(colorama.Fore.BLUE + record.msg)
        elif "CLAUDE→OBRA" in record.msg:
            print(colorama.Fore.GREEN + record.msg)
        # ... etc
```

**CLI Flag** (`src/cli.py`):
```python
@task.command()
@click.argument('task_id', type=int)
@click.option('--stream', is_flag=True, help='Enable real-time streaming')
def execute(task_id: int, stream: bool):
    orchestrator.execute_task(task_id, stream=stream)
```

**Orchestrator** (`src/orchestrator.py`):
```python
def execute_task(self, task_id: int, stream: bool = False):
    if stream:
        handler = StreamingHandler()
        self.logger.addHandler(handler)
    # ... rest of execution
```

---

## Phase 2: Interactive (2-3 hours)

### Files to Create

```
src/utils/command_processor.py    # Command parsing and execution
src/utils/input_manager.py        # Non-blocking input thread
```

### Files to Modify

```
src/orchestrator.py    # Add interactive mode, pause/resume, injection
src/cli.py             # Add --interactive flag
```

### Key Code Locations

**CommandProcessor** (`src/utils/command_processor.py`):
```python
class CommandProcessor:
    def __init__(self):
        self.commands = {
            '/to-claude': self._to_claude,
            '/to-obra': self._to_obra,
            '/pause': self._pause,
            # ... etc
        }

    def parse_command(self, input: str) -> Tuple[str, Dict]:
        # Parse "/to-claude message" → ('/to-claude', {'message': 'message'})
        pass
```

**InputManager** (`src/utils/input_manager.py`):
```python
class InputManager:
    def __init__(self):
        self.queue = Queue()
        self.thread = Thread(target=self._input_loop, daemon=True)

    def _input_loop(self):
        while True:
            cmd = input('> ')  # Use prompt_toolkit for better UX
            self.queue.put(cmd)
```

**Interactive Integration** (`src/orchestrator.py`):
```python
def _execute_single_task(self, ...):
    # After each iteration
    if self.interactive_mode:
        cmd = self._wait_for_user_input('> ')
        if cmd:
            self.command_processor.execute_command(cmd)

    # Before agent.send_prompt()
    if self.injected_context:
        prompt = self._apply_injected_context(prompt, self.injected_context)
        self.injected_context = {}
```

---

## Testing Checklist

### Phase 1 Tests

```bash
# Unit test
pytest tests/test_streaming_handler.py -v

# Integration test
./venv/bin/python -m src.cli task execute 3 --stream

# Expected output:
# [OBRA→CLAUDE] Sending prompt (1324 chars)...  (blue)
# [CLAUDE→OBRA] Response received (3493 chars)  (green)
# [QWEN] Quality: 0.76 (PASS)                   (yellow)
```

### Phase 2 Tests

```bash
# Unit tests
pytest tests/test_command_processor.py -v
pytest tests/test_input_manager.py -v
pytest tests/test_orchestrator_interactive.py -v

# Integration test
./venv/bin/python -m src.cli task execute 3 --stream --interactive

# Test sequence:
# 1. Wait for "> " prompt after iteration 1
# 2. Type: /to-claude Add unit tests
# 3. Press Enter
# 4. Verify message appears in next Claude prompt
# 5. Type: /pause
# 6. Verify execution stops
# 7. Type: /resume
# 8. Verify execution continues
```

---

## Common Issues & Fixes

### Issue: Colors don't show on Windows

**Fix**: Install colorama and call `colorama.init()`
```python
import colorama
colorama.init()  # Must call on Windows
```

### Issue: Input blocks main thread

**Fix**: Use daemon thread and timeout
```python
thread = Thread(target=input_loop, daemon=True)
thread.start()
# Never join() without timeout!
```

### Issue: Commands not recognized

**Fix**: Check command registry
```python
# CommandProcessor.__init__
self.commands = {
    '/to-claude': self._to_claude,
    # Make sure all commands are registered!
}
```

### Issue: Injected context not appearing

**Fix**: Check context application timing
```python
# Must apply BEFORE agent.send_prompt(), not after!
if self.injected_context:
    prompt = self._apply_injected_context(prompt, self.injected_context)
    self.injected_context = {}  # Clear after use!
```

---

## Dependencies

```bash
# Phase 1-2
pip install colorama>=0.4.6
pip install prompt-toolkit>=3.0.0

# Phase 3 (TUI, future)
pip install textual>=0.40.0
pip install pygments>=2.16.0
```

Update `requirements.txt`:
```txt
colorama>=0.4.6
prompt-toolkit>=3.0.0
```

---

## Code Snippets

### Streaming Handler Template

```python
# src/utils/streaming_handler.py
import logging
import colorama
from typing import Dict

colorama.init()

class StreamingHandler(logging.Handler):
    """Custom handler for real-time colored output."""

    COLOR_MAP: Dict[str, str] = {
        'OBRA→CLAUDE': colorama.Fore.BLUE,
        'CLAUDE→OBRA': colorama.Fore.GREEN,
        'QWEN': colorama.Fore.YELLOW,
        'ERROR': colorama.Fore.RED,
        'DECISION': colorama.Fore.CYAN,
    }

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)

        # Color based on content
        color = colorama.Fore.WHITE
        for keyword, keyword_color in self.COLOR_MAP.items():
            if keyword in msg:
                color = keyword_color
                break

        # Print with color
        print(f"{color}{msg}{colorama.Style.RESET_ALL}")
```

### Command Processor Template

```python
# src/utils/command_processor.py
from typing import Dict, Tuple, Callable, Any
import re

class CommandProcessor:
    """Parse and execute user commands."""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.commands: Dict[str, Callable] = {
            '/pause': self._pause,
            '/resume': self._resume,
            '/to-claude': self._to_claude,
            '/to-obra': self._to_obra,
            '/override-decision': self._override_decision,
            '/status': self._status,
            '/help': self._help,
            '/stop': self._stop,
        }

    def parse_command(self, input_str: str) -> Tuple[str, Dict[str, Any]]:
        """Parse command and extract arguments."""
        match = re.match(r'^(/\S+)\s*(.*)', input_str.strip())
        if not match:
            return ('', {})

        cmd, args_str = match.groups()
        args = {'message': args_str} if args_str else {}
        return (cmd, args)

    def execute_command(self, input_str: str) -> Dict[str, Any]:
        """Execute parsed command."""
        cmd, args = self.parse_command(input_str)

        if cmd not in self.commands:
            return {'error': f'Unknown command: {cmd}. Type /help for help.'}

        try:
            return self.commands[cmd](args)
        except Exception as e:
            return {'error': f'Command failed: {str(e)}'}

    def _to_claude(self, args: Dict) -> Dict:
        """Inject message into Claude's next prompt."""
        message = args.get('message', '')
        if not message:
            return {'error': '/to-claude requires a message'}

        self.orchestrator.injected_context['to_claude'] = message
        return {'success': f'Will send to Claude: {message}'}

    # ... implement other command handlers
```

### Input Manager Template

```python
# src/utils/input_manager.py
from queue import Queue, Empty
from threading import Thread
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

class InputManager:
    """Non-blocking user input manager."""

    COMMANDS = ['/pause', '/resume', '/to-claude', '/to-obra',
                '/override-decision', '/status', '/help', '/stop']

    def __init__(self):
        self.queue = Queue()
        self.thread = None
        self.running = False
        self.completer = WordCompleter(self.COMMANDS)

    def start_listening(self):
        """Start input listener thread."""
        self.running = True
        self.thread = Thread(target=self._input_loop, daemon=True)
        self.thread.start()

    def _input_loop(self):
        """Input loop running in separate thread."""
        while self.running:
            try:
                # Use prompt_toolkit for better UX
                cmd = prompt('> ', completer=self.completer)
                self.queue.put(cmd)
            except (EOFError, KeyboardInterrupt):
                self.queue.put('/stop')
                break

    def get_command(self, timeout: float = 0.1) -> str | None:
        """Get command from queue (non-blocking)."""
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return None

    def stop_listening(self):
        """Stop input listener thread."""
        self.running = False
```

---

## Output Format Examples

### Streaming Output (Phase 1)

```
[OBRA→CLAUDE] Iteration 1/10
[OBRA→CLAUDE] Sending prompt (1324 chars)...

[CLAUDE] Turn 1/10: Creating project structure...
[CLAUDE] Turn 2/10: Installing GUT framework...
[CLAUDE] Turn 3/10: Configuring git repository...

[CLAUDE→OBRA] Response received (3493 chars)
[CLAUDE→OBRA] Files created: 245
[CLAUDE→OBRA] Turns used: 3/10

[QWEN] Validating response...
[QWEN] Quality: 0.76 (PASS)
[QWEN] Confidence: 0.64

[OBRA] Decision: PROCEED
[OBRA] Reason: Quality threshold met, no errors detected

────────────────────────────────────────────────────────────────
```

### Interactive Output (Phase 2)

```
[OBRA→CLAUDE] Iteration 1/10
[OBRA→CLAUDE] Sending prompt (1324 chars)...
[CLAUDE→OBRA] Response received (3493 chars)
[QWEN] Quality: 0.76 (PASS)
[OBRA] Decision: PROCEED

> /to-claude Add unit tests to tests/ directory
✓ Will inject to Claude: Add unit tests to tests/ directory

[OBRA→CLAUDE] Iteration 2/10
[OBRA→CLAUDE] USER GUIDANCE: Add unit tests to tests/ directory
[OBRA→CLAUDE] Sending prompt (1487 chars)...

> /pause
⏸ Execution paused. Type /resume to continue.

> /status
📊 Task Status:
   Task ID: 3
   Iteration: 2/10
   Quality: 0.76
   Turns used: 6/20
   Files created: 245

> /resume
▶ Resuming execution...
```

---

## Evolution to TUI (Phase 3)

When ready to implement TUI:

1. Install textual: `pip install textual>=0.40.0`
2. Create `src/cli_tui.py`:

```python
from textual.app import App
from textual.widgets import Header, Footer, Static, Input
from textual.containers import Container

class ObraTUI(App):
    def compose(self):
        yield Header()
        yield Container(
            Static(id="obra-panel"),      # Left: Obra prompts
            Static(id="claude-panel"),    # Right: Claude responses
            Static(id="qwen-panel"),      # Bottom: Validation
            Input(placeholder="Command..."),
        )
        yield Footer()
```

3. Add CLI flag: `./venv/bin/python -m src.cli task execute 3 --tui`

---

## Performance Benchmarks

Target metrics:

```json
{
  "streaming_overhead": "< 5% vs non-streaming",
  "command_latency": "< 50ms from input to execution",
  "memory_overhead": "< 10MB for input thread",
  "no_deadlocks": "0 occurrences in 100 test runs"
}
```

Benchmark commands:

```bash
# Benchmark streaming overhead
time ./venv/bin/python -m src.cli task execute 3
time ./venv/bin/python -m src.cli task execute 3 --stream

# Should be < 5% difference
```

---

## Troubleshooting Commands

```bash
# Check if colorama works
python -c "import colorama; colorama.init(); print(colorama.Fore.GREEN + 'SUCCESS')"

# Check if prompt_toolkit works
python -c "from prompt_toolkit import prompt; prompt('> ')"

# Test streaming handler directly
python -c "
from src.utils.streaming_handler import StreamingHandler
import logging
logger = logging.getLogger()
logger.addHandler(StreamingHandler())
logger.warning('OBRA→CLAUDE Test message')
"

# Check thread safety
python tests/test_input_manager.py -v -k test_thread_safety
```

---

## Next Steps After Implementation

1. **Test with Tetris project**: Continue Milestone 1 with `--stream --interactive`
2. **Gather feedback**: Note pain points and UX issues
3. **Iterate**: Improve based on real usage
4. **Document**: Write user guide at `docs/guides/INTERACTIVE_MODE_GUIDE.md`
5. **Plan TUI**: When streaming is stable, start TUI planning

---

**Quick Start**: Read this → Implement Phase 1 → Test → Implement Phase 2 → Test → Ship!
