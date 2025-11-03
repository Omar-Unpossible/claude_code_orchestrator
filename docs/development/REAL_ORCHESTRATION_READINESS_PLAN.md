# Real Orchestration Readiness Plan

**Goal**: Get to hands-on-keyboard testing where Obra orchestrates Claude Code with real LLM validation

**Status**: All code exists (M0-M8 complete), needs verification and integration testing

**Timeline**: 4-6 hours of focused work

---

## Current Situation Analysis

### ✅ What We Have (Implemented)

**Core Infrastructure** (M0-M1):
- ✅ Plugin system (AgentPlugin, LLMPlugin)
- ✅ StateManager with full CRUD operations
- ✅ Configuration system
- ✅ Database models and schema
- ✅ Exception handling

**LLM & Agents** (M2, M8):
- ✅ LocalLLMInterface (Ollama integration)
- ✅ PromptGenerator (creates prompts)
- ✅ ResponseValidator (validates responses)
- ✅ ClaudeCodeLocalAgent (subprocess management)
- ✅ ClaudeCodeSSHAgent (remote execution)
- ✅ MockAgent (for testing)

**Monitoring** (M3):
- ✅ FileWatcher (tracks file changes)
- ✅ OutputMonitor (parses agent output)

**Orchestration** (M4):
- ✅ DecisionEngine (makes decisions)
- ✅ QualityController (scores quality)
- ✅ BreakpointManager (triggers breakpoints)
- ✅ TaskScheduler (manages tasks)

**Utilities** (M5):
- ✅ ContextManager (builds context)
- ✅ ConfidenceScorer (calculates confidence)
- ✅ TokenCounter (counts tokens)

**Integration** (M6):
- ✅ Orchestrator (main loop)
- ✅ CLI (command-line interface)
- ✅ Interactive mode

### ⚠️ What's Missing/Untested

1. **Component Verification**: Individual components not tested with real inputs
2. **Integration Testing**: Components not tested working together
3. **Orchestrator Testing**: Never called `Orchestrator.execute_task()` with real agent
4. **LLM Connectivity**: Ollama integration not verified
5. **Agent Communication**: ClaudeCodeLocalAgent subprocess not tested with real Claude
6. **Error Paths**: Breakpoints, retries, escalations not validated
7. **End-to-End Flow**: Complete workflow never executed

---

## Phase 1: Component Verification (2 hours)

**Goal**: Verify each component can be instantiated and works independently

### 1.1: Core Components (30 min)

**StateManager**:
```bash
# Already tested in runthrough ✅
```

**Config**:
```bash
# Already works ✅
```

### 1.2: LLM Components (30 min)

**Test LocalLLMInterface** ⚠️:
```python
# Create: tests/test_llm_integration.py
from src.llm.local_interface import LocalLLMInterface

def test_ollama_connection():
    """Test connection to Ollama."""
    config = {
        'type': 'ollama',
        'api_url': 'http://localhost:11434',
        'model': 'qwen2.5-coder:32b'
    }
    llm = LocalLLMInterface(config)

    # Test simple generation
    response = llm.generate("Say hello")
    assert len(response) > 0
    assert 'hello' in response.lower()
```

**Test PromptGenerator** ⚠️:
```python
def test_prompt_generator():
    """Test prompt generation."""
    from src.llm.prompt_generator import PromptGenerator
    from src.core.models import Task

    llm = LocalLLMInterface(config)  # Mock or real
    generator = PromptGenerator(llm)

    task = Task(title="Create calculator", description="...")
    context = {'files': [], 'history': []}

    prompt = generator.generate_prompt(task, context)
    assert len(prompt) > 0
    assert 'calculator' in prompt.lower()
```

**Test ResponseValidator** ⚠️:
```python
def test_response_validator():
    """Test response validation."""
    from src.llm.response_validator import ResponseValidator

    validator = ResponseValidator(llm)

    # Valid response
    response = "Here's the code:\n```python\nprint('hello')\n```"
    result = validator.validate_response(response)
    assert result['valid'] == True

    # Invalid response
    response = "I can't do that"
    result = validator.validate_response(response)
    assert result['valid'] == False
```

### 1.3: Agent Components (30 min)

**Test MockAgent** ✅:
```bash
# Already works in runthrough
```

**Test ClaudeCodeLocalAgent** ⚠️:
```python
def test_local_agent_subprocess():
    """Test agent can start Claude Code."""
    from src.agents.claude_code_local import ClaudeCodeLocalAgent

    agent = ClaudeCodeLocalAgent()
    config = {
        'command': 'claude',
        'workspace_dir': '/tmp/test_workspace',
        'timeout_ready': 30,
        'timeout_response': 120
    }

    try:
        agent.initialize(config)
        assert agent.is_healthy()

        # Simple test prompt
        response = agent.send_prompt("echo 'Hello from Claude'")
        assert len(response) > 0

    finally:
        agent.cleanup()
```

### 1.4: Orchestration Components (30 min)

**Test QualityController** ⚠️:
```python
def test_quality_controller():
    """Test quality scoring."""
    from src.orchestration.quality_controller import QualityController

    controller = QualityController(state_manager, config={})

    # Test code quality
    response = "```python\ndef add(a, b):\n    return a + b\n```"
    task = Task(title="Create calculator")

    result = controller.validate_output(response, task, {'language': 'python'})
    assert result.overall_score > 0
    assert result.overall_score <= 100
```

**Test ConfidenceScorer** ⚠️:
```python
def test_confidence_scorer():
    """Test confidence calculation."""
    from src.utils.confidence_scorer import ConfidenceScorer

    scorer = ConfidenceScorer(config={})

    response = "Complete calculator implementation"
    task = Task(title="Create calculator")
    metadata = {
        'validation': {'valid': True},
        'quality': type('obj', (object,), {'overall_score': 85})()
    }

    confidence = scorer.score_response(response, task, metadata)
    assert 0 <= confidence <= 100
```

**Test DecisionEngine** ⚠️:
```python
def test_decision_engine():
    """Test decision making."""
    from src.orchestration.decision_engine import DecisionEngine

    engine = DecisionEngine(state_manager, breakpoint_manager, config={})

    context = {
        'task': task,
        'response': "Good code",
        'validation_result': {'valid': True},
        'quality_score': 85,
        'confidence_score': 75
    }

    action = engine.decide_next_action(context)
    assert action.type in ['proceed', 'retry', 'clarify', 'escalate']
```

**Deliverable**: `tests/test_component_verification.py` with all component tests

---

## Phase 2: Integration Testing (1.5 hours)

**Goal**: Test components working together without real Claude API

### 2.1: Orchestrator Initialization (30 min)

**Test** ⚠️:
```python
def test_orchestrator_initialization():
    """Test Orchestrator can initialize all components."""
    from src.orchestrator import Orchestrator

    config = Config.load('config/test_config.yaml')
    config.set('agent.type', 'mock')  # Use mock for now

    orch = Orchestrator(config=config)

    # Should not raise
    orch.initialize()

    # Verify components initialized
    assert orch.state_manager is not None
    assert orch.agent is not None
    assert orch.llm_interface is not None
    assert orch.prompt_generator is not None
    assert orch.response_validator is not None
    assert orch.quality_controller is not None
    assert orch.confidence_scorer is not None
    assert orch.decision_engine is not None

    print("✅ Orchestrator initialization: PASS")
```

### 2.2: Task Execution with Mock Agent (45 min)

**Test** ⚠️:
```python
def test_orchestrator_execute_task_mock():
    """Test full execution with mock agent."""
    config = Config.load('config/test_config.yaml')
    config.set('agent.type', 'mock')

    orch = Orchestrator(config=config)
    orch.initialize()

    # Create project and task
    project = orch.state_manager.create_project(
        name="Test Project",
        description="Test",
        working_dir="/tmp/test_workspace"
    )

    task = orch.state_manager.create_task(
        project_id=project.id,
        task_data={
            'title': 'Create Calculator',
            'description': 'Create Python calculator with add, subtract, multiply, divide'
        }
    )

    # Execute task
    result = orch.execute_task(task.id, max_iterations=3)

    # Verify
    assert result['status'] in ['completed', 'escalated']
    assert 'response' in result
    assert result['iterations'] > 0

    print(f"✅ Task execution: {result['status']}")
    print(f"   Iterations: {result['iterations']}")
    print(f"   Quality: {result.get('quality_score', 'N/A')}")
    print(f"   Confidence: {result.get('confidence', 'N/A')}")
```

### 2.3: Data Flow Validation (15 min)

**Test** ⚠️:
```python
def test_orchestrator_data_flow():
    """Test data flows correctly through pipeline."""
    # ... setup orchestrator with mock agent

    # Monitor each step
    steps_completed = []

    # Patch components to track calls
    original_generate = orch.prompt_generator.generate_prompt
    def tracked_generate(*args, **kwargs):
        steps_completed.append('prompt_generated')
        return original_generate(*args, **kwargs)
    orch.prompt_generator.generate_prompt = tracked_generate

    # Similar for other components...

    # Execute
    result = orch.execute_task(task.id)

    # Verify all steps executed
    expected_steps = [
        'prompt_generated',
        'agent_called',
        'response_validated',
        'quality_checked',
        'confidence_scored',
        'decision_made'
    ]

    for step in expected_steps:
        assert step in steps_completed, f"Missing step: {step}"

    print("✅ Data flow: PASS")
```

**Deliverable**: `tests/test_orchestrator_integration.py` with integration tests

---

## Phase 3: Real Agent Integration (1.5 hours)

**Goal**: Test with real ClaudeCodeLocalAgent and Ollama

### 3.1: Environment Setup (15 min)

**Checklist**:
- [ ] Ollama installed and running
- [ ] Qwen model pulled: `ollama pull qwen2.5-coder:32b`
- [ ] Claude Code CLI installed: `npm install -g @anthropics/claude-code`
- [ ] API key set: `export ANTHROPIC_API_KEY=sk-ant-...`
- [ ] Test workspace created: `mkdir -p /tmp/obra_real_test`

**Verification**:
```bash
# Test Ollama
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5-coder:32b","prompt":"Say hello","stream":false}'

# Test Claude Code CLI
claude --version

# Test workspace
ls -la /tmp/obra_real_test
```

### 3.2: Configuration for Real Test (15 min)

**Create** `config/real_agent_config.yaml`:
```yaml
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434
  temperature: 0.7
  timeout: 30
  max_tokens: 4096

agent:
  type: claude_code_local  # ← REAL AGENT
  timeout: 120
  max_retries: 3

  local:
    command: claude
    workspace_dir: /tmp/obra_real_test/workspace
    timeout_ready: 30
    timeout_response: 120

database:
  url: sqlite:///data/orchestrator_real_test.db
  echo: true  # ← Enable SQL logging for debugging

orchestration:
  max_iterations: 5
  iteration_timeout: 300

breakpoints:
  enabled: true
  triggers:
    low_confidence:
      enabled: true
      threshold: 30
    quality_too_low:
      enabled: true
      threshold: 50

validation:
  quality:
    enabled: true
    threshold: 70

confidence:
  threshold: 50

logging:
  level: DEBUG  # ← Enable debug logging
  file: logs/real_agent_test.log
```

### 3.3: First Real Test (Simple Task) (30 min)

**Test Script**: `scripts/test_real_orchestration.py`
```python
#!/usr/bin/env python3
"""Test real orchestration with Claude Code and Ollama."""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import Config
from src.orchestrator import Orchestrator

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/real_agent_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("="*80)
    logger.info("REAL ORCHESTRATION TEST")
    logger.info("="*80)

    # Load config with real agent
    config = Config.load('config/real_agent_config.yaml')

    # Create orchestrator
    logger.info("Creating orchestrator...")
    orch = Orchestrator(config=config)

    # Initialize
    logger.info("Initializing components...")
    orch.initialize()
    logger.info("✓ Initialized")

    # Create project
    logger.info("Creating project...")
    project = orch.state_manager.create_project(
        name="Real Test Project",
        description="Testing real orchestration with Claude",
        working_dir="/tmp/obra_real_test/workspace"
    )
    logger.info(f"✓ Project created: {project.id}")

    # Create simple task
    logger.info("Creating task...")
    task = orch.state_manager.create_task(
        project_id=project.id,
        task_data={
            'title': 'Create Hello World',
            'description': 'Create a Python script that prints "Hello, World!"'
        }
    )
    logger.info(f"✓ Task created: {task.id}")

    # Execute task
    logger.info("="*80)
    logger.info("EXECUTING TASK")
    logger.info("="*80)

    try:
        result = orch.execute_task(task.id, max_iterations=3)

        logger.info("="*80)
        logger.info("RESULT")
        logger.info("="*80)
        logger.info(f"Status: {result['status']}")
        logger.info(f"Iterations: {result['iterations']}")
        logger.info(f"Quality Score: {result.get('quality_score', 'N/A')}")
        logger.info(f"Confidence: {result.get('confidence', 'N/A')}")
        logger.info(f"Response length: {len(result.get('response', ''))}")

        if result['status'] == 'completed':
            logger.info("✅ TEST PASSED")
            return 0
        else:
            logger.warning(f"⚠️ TEST INCOMPLETE: {result['status']}")
            return 1

    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup
        if orch.agent:
            orch.agent.cleanup()

if __name__ == '__main__':
    sys.exit(main())
```

**Run**:
```bash
chmod +x scripts/test_real_orchestration.py
python scripts/test_real_orchestration.py
```

### 3.4: Debug and Fix Issues (30 min)

**Common Issues**:

1. **Ollama Connection Failed**:
```bash
# Check Ollama
systemctl status ollama
curl http://localhost:11434/api/tags

# Restart if needed
systemctl restart ollama
```

2. **Claude Code Not Found**:
```bash
# Check installation
which claude
claude --version

# Install if missing
npm install -g @anthropics/claude-code
```

3. **API Key Issues**:
```bash
# Verify key
echo $ANTHROPIC_API_KEY

# Set if missing
export ANTHROPIC_API_KEY=sk-ant-...
```

4. **Agent Timeout**:
- Increase `timeout_ready` and `timeout_response`
- Check Claude Code starts: `claude --version`
- Check logs: `tail -f logs/real_agent_test.log`

5. **Quality/Confidence Too Low**:
- Check thresholds in config
- Review QualityController logic
- May need to adjust scoring

**Deliverable**: Working real orchestration with simple task

---

## Phase 4: Hands-On-Keyboard Test (1 hour)

**Goal**: Manual validation with real task, monitoring, and interaction

### 4.1: Setup Monitoring (15 min)

**Terminal Layout**:
```
┌─────────────────────────────────┬─────────────────────────────────┐
│ Terminal 1: Test Execution      │ Terminal 2: Logs                │
│ python scripts/test_real_...py  │ tail -f logs/real_agent_test.log│
├─────────────────────────────────┼─────────────────────────────────┤
│ Terminal 3: Database Monitor    │ Terminal 4: Workspace Monitor   │
│ watch -n 2 'python query_db.py' │ watch -n 1 'ls -lt /tmp/obra...'│
└─────────────────────────────────┴─────────────────────────────────┘
```

**Database Monitor Script**: `scripts/query_db.py`
```python
#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/orchestrator_real_test.db')
cursor = conn.cursor()

print("Projects:")
cursor.execute("SELECT id, project_name, status FROM project_state")
for row in cursor.fetchall():
    print(f"  {row}")

print("\nTasks:")
cursor.execute("SELECT id, title, status FROM task ORDER BY updated_at DESC LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
```

### 4.2: Execute Real Calculator Task (20 min)

**Task**: The calculator we used in mock test, but with real Claude

**Modified Test Script**:
```python
task = orch.state_manager.create_task(
    project_id=project.id,
    task_data={
        'title': 'Create Python Calculator',
        'description': '''Create a Python calculator with the following:

        1. Functions: add, subtract, multiply, divide
        2. Error handling for division by zero
        3. Unit tests using pytest
        4. Docstrings for all functions

        Create two files:
        - calculator.py (implementation)
        - test_calculator.py (tests)
        '''
    }
)
```

**Observe**:
- ✓ Agent initialization in logs
- ✓ Prompt generation
- ✓ Claude response
- ✓ Files created in workspace
- ✓ Validation results
- ✓ Quality score
- ✓ Confidence score
- ✓ Decision made
- ✓ Task completion

### 4.3: Test Breakpoint Trigger (15 min)

**Task**: Ambiguous task that should trigger breakpoint

```python
task = orch.state_manager.create_task(
    project_id=project.id,
    task_data={
        'title': 'Improve the code',
        'description': 'Make it better'  # Intentionally vague
    }
)
```

**Expected**:
- Low quality score (< 50)
- Breakpoint triggered
- Status: 'escalated'
- Reason logged

**Verify**:
```python
# Check breakpoint in database
cursor.execute("""
    SELECT id, reason, status
    FROM breakpoint
    WHERE task_id = ?
""", (task.id,))
```

### 4.4: Test Multi-Iteration Task (10 min)

**Task**: Complex task requiring multiple iterations

```python
task = orch.state_manager.create_task(
    project_id=project.id,
    task_data={
        'title': 'Create Calculator with GUI',
        'description': '''Create a calculator application with:

        1. Core calculator functions (add, subtract, multiply, divide)
        2. Simple GUI using tkinter
        3. Unit tests for calculator logic
        4. Error handling

        Build incrementally, testing after each component.
        '''
    }
)
```

**Observe**:
- Multiple iterations (should be 2-3)
- Context building across iterations
- Quality improving over iterations
- Final integration

### 4.5: Validation Checklist (Manual)

**Run through validation checklist** from `VALIDATION_CHECKLIST.md`:

- [ ] Agent starts successfully
- [ ] Prompt generated correctly
- [ ] Claude responds
- [ ] Response validated
- [ ] Quality scored
- [ ] Confidence calculated
- [ ] Decision made correctly
- [ ] Files created in workspace
- [ ] Tests run (if generated)
- [ ] State persisted
- [ ] Breakpoints work
- [ ] Multi-iteration works
- [ ] Error handling works

**Deliverable**: Completed validation checklist with notes

---

## Phase 5: Documentation and Handoff (30 min)

### 5.1: Create Test Report

**Document**: `docs/development/REAL_ORCHESTRATION_TEST_REPORT.md`

**Contents**:
- Test environment details
- Tests executed
- Results (pass/fail)
- Issues encountered
- Workarounds applied
- Performance metrics
- Screenshots/logs
- Recommendations

### 5.2: Update Documentation

**Update**:
- `README.md` - Mark M8 as tested
- `CLAUDE.md` - Update status to "Real-world validated"
- `M8_COMPLETION_SUMMARY.md` - Add test results

### 5.3: Create Quick Start Guide

**Document**: `docs/guides/QUICK_START_REAL_AGENT.md`

**Contents**:
- Prerequisites
- Setup (5 minutes)
- First real test (10 minutes)
- Troubleshooting
- Examples

---

## Success Criteria

### Phase 1: Component Verification ✅
- [ ] All components can be instantiated
- [ ] LLM interface connects to Ollama
- [ ] Agent subprocess starts
- [ ] Validators work with sample inputs
- [ ] Scorers return valid scores

### Phase 2: Integration ✅
- [ ] Orchestrator.initialize() succeeds
- [ ] execute_task() works with mock agent
- [ ] Data flows through all components
- [ ] State persists correctly

### Phase 3: Real Agent ✅
- [ ] ClaudeCodeLocalAgent subprocess starts
- [ ] Agent sends/receives from Claude
- [ ] Simple task completes end-to-end
- [ ] Files generated in workspace

### Phase 4: Hands-On-Keyboard ✅
- [ ] Real calculator task completes
- [ ] Breakpoint triggers correctly
- [ ] Multi-iteration task works
- [ ] All components validated manually

### Phase 5: Documentation ✅
- [ ] Test report completed
- [ ] Documentation updated
- [ ] Quick start guide created

---

## Risk Assessment

### High Risk
- **Ollama/Qwen availability**: Requires GPU, may not be accessible
  - *Mitigation*: Test with smaller model first (qwen2.5-coder:7b)
- **Claude API rate limits**: May hit limits during testing
  - *Mitigation*: Use breakpoints, test incrementally
- **Agent communication**: Complex subprocess management
  - *Mitigation*: Extensive logging, step-by-step debugging

### Medium Risk
- **Quality scoring accuracy**: Heuristics may not work well
  - *Mitigation*: Tune thresholds based on test results
- **Confidence calculation**: May be too conservative
  - *Mitigation*: Adjust weights in config
- **Breakpoint sensitivity**: May trigger too often or not enough
  - *Mitigation*: Test with various scenarios, tune thresholds

### Low Risk
- **State persistence**: Already tested ✅
- **File monitoring**: Already tested ✅
- **Configuration**: Already working ✅

---

## Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Component Verification | 2h | 2h |
| Phase 2: Integration Testing | 1.5h | 3.5h |
| Phase 3: Real Agent Integration | 1.5h | 5h |
| Phase 4: Hands-On-Keyboard | 1h | 6h |
| Phase 5: Documentation | 0.5h | 6.5h |
| **Total** | **~6.5 hours** | **Focused work** |

**Realistic**: 2-3 days with breaks, debugging, and iteration

---

## Next Immediate Steps

1. **RIGHT NOW** (15 min):
   ```bash
   # Create component verification test file
   touch tests/test_component_verification.py

   # Start with LLM test
   # Copy test from Section 1.2 above
   ```

2. **Next** (30 min):
   ```bash
   # Run component tests one by one
   pytest tests/test_component_verification.py::test_ollama_connection -v
   pytest tests/test_component_verification.py::test_prompt_generator -v
   # etc.
   ```

3. **Then** (1 hour):
   ```bash
   # Create integration test
   touch tests/test_orchestrator_integration.py

   # Test Orchestrator.initialize()
   pytest tests/test_orchestrator_integration.py -v
   ```

4. **Finally** (2 hours):
   ```bash
   # Create real agent test script
   touch scripts/test_real_orchestration.py

   # Run first real test
   python scripts/test_real_orchestration.py
   ```

---

## Appendix: Quick Reference Commands

### Check Prerequisites
```bash
# Ollama
curl http://localhost:11434/api/tags

# Claude Code
claude --version

# API Key
echo $ANTHROPIC_API_KEY

# Python
python --version
```

### Run Tests
```bash
# Component tests
pytest tests/test_component_verification.py -v

# Integration tests
pytest tests/test_orchestrator_integration.py -v

# Real agent test
python scripts/test_real_orchestration.py
```

### Monitor
```bash
# Logs
tail -f logs/real_agent_test.log

# Database
python scripts/query_db.py

# Workspace
ls -ltr /tmp/obra_real_test/workspace/

# Agent process
ps aux | grep claude
```

### Debug
```bash
# Enable debug logging
export OBRA_LOG_LEVEL=DEBUG

# Test individual components
python -c "from src.llm.local_interface import LocalLLMInterface; ..."

# Check agent health
python -c "from src.agents.claude_code_local import *; agent = ...; print(agent.is_healthy())"
```

---

**Status**: Ready to begin Phase 1
**Last Updated**: 2025-11-02
**Estimated Completion**: 2-3 days
