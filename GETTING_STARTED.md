# IMPLEMENTATION SEED PROMPT FOR CLAUDE CODE

I need you to implement a Claude Code orchestration system according to the detailed multi-file implementation plan.

## Project Overview

You're building a system where a **local LLM (Qwen on RTX 5090)** acts as an intelligent supervisor that:
1. Monitors **Claude Code CLI** (running in WSL2)
2. Validates Claude Code's work using fast local inference
3. Generates optimized follow-up prompts
4. Detects when human intervention is needed (breakpoints)
5. Tracks all changes and maintains project state

This enables **semi-autonomous software development** where Claude Code does the heavy lifting, and the local LLM provides oversight and continuity.

## Implementation Plan Structure

The implementation plan is split into multiple files for easier navigation:

### 📋 Start Here
- **`IMPLEMENTATION_PLAN.md`** - High-level roadmap (READ THIS FIRST - 10 min)
  - Project vision and architecture summary
  - 8 milestones with dependencies
  - Progress tracking
  - Success metrics

### 📁 Detailed Plans (plans/ directory)
- **`00_architecture_overview.json`** - Plugin system & architecture decisions
- **`01_foundation.json`** - Core infrastructure (database, state, config)
- **`02_interfaces.json`** - LLM & agent interfaces
- **`03_monitoring.json`** - File watching
- **`04_orchestration.json`** - Task scheduling & decisions
- **`05_utilities.json`** - Token counting, context management
- **`06_integration.json`** - Main loop & CLI
- **`07_deployment.json`** - Testing & deployment

## Your Task: Start with Milestone 0 (Architecture Foundation)

### Step 1: Read the Plans (30 minutes)
```bash
# Read in this order:
1. IMPLEMENTATION_PLAN.md (overview)
2. plans/00_architecture_overview.json (architecture & plugins)
3. plans/01_foundation.json (what you'll build after M0)
```

### Step 2: Understand the Architecture

**Key Architectural Principles:**
1. ✅ **Plugin system** - Agent and LLM are pluggable (enables flexibility)
2. ✅ **StateManager is single source of truth** - all state goes through it
3. ✅ **No cost tracking** - using Claude subscription, not API
4. ✅ **Validation before quality control** - order matters
5. ✅ **File watching tracks Claude Code's changes** - enables rollback
6. ✅ **SSH to VM for safety** - Claude Code runs in isolated VM

**What This System Does:**
```
Local LLM (Qwen) generates prompt
    ↓
Sends to Claude Code (in VM via SSH)
    ↓
Monitors output + watches file changes
    ↓
Validates response (local LLM)
    ↓
Decides next action (proceed/retry/escalate)
    ↓
Repeat until task complete or breakpoint
```

### Step 3: Begin Implementation - Milestone 0

**M0 Deliverables (8 hours estimated):**
- **0.1**: Plugin interfaces (AgentPlugin, LLMPlugin abstract base classes)
- **0.2**: Plugin registry (decorator-based registration)
- **0.3**: Architecture documentation (design decisions, diagrams, ADRs)

**Implementation order:** 0.1 → 0.2 → 0.3

**Read the detailed requirements:**
```bash
# Open and read:
plans/00_architecture_overview.json
# Pay special attention to:
# - "deliverables" section (what to build)
# - "acceptance_criteria" (definition of done)
# - "implementation_notes" (how to build it)
```

### Step 4: Create Project Structure

Before coding, create the directory structure:
```
claude_code_orchestrator/
├── src/
│   ├── core/              # M1: State, config, models, exceptions
│   ├── llm/               # M2: Local LLM interface, prompts, validation
│   ├── agents/            # M2: Claude Code agent implementations
│   ├── monitoring/        # M3: File watching, event detection
│   ├── orchestration/     # M4: Task scheduling, decisions, breakpoints
│   ├── utils/             # M5: Token counting, context, confidence
│   └── plugins/           # M0: START HERE - Plugin base classes
│       ├── __init__.py
│       ├── base.py        # 0.1: AgentPlugin, LLMPlugin interfaces
│       ├── registry.py    # 0.2: Registration system
│       └── exceptions.py
├── tests/
│   ├── conftest.py
│   ├── mocks/             # Mock plugins for testing
│   └── test_plugins.py    # Tests for M0
├── config/
│   ├── default_config.yaml
│   ├── prompt_templates.yaml
│   └── breakpoint_rules.yaml
├── docs/
│   ├── architecture/      # 0.3: Architecture docs
│   │   ├── system_design.md
│   │   ├── plugin_system.md
│   │   └── data_flow.md
│   └── decisions/         # 0.3: Architecture Decision Records
│       ├── 001_why_plugins.md
│       ├── 002_deployment_models.md
│       └── 003_state_management.md
├── data/                  # Runtime data (created at runtime)
├── logs/                  # Logs (created at runtime)
├── IMPLEMENTATION_PLAN.md
├── plans/                 # Detailed JSON plans
├── README.md
├── requirements.txt
└── setup.py
```

### Step 5: Implement Deliverable 0.1 - Plugin Interfaces

**File: `src/plugins/base.py`**

**What to build:**
```python
from abc import ABC, abstractmethod
from typing import List, Optional, Iterator
from pathlib import Path

class AgentPlugin(ABC):
    """Abstract base class for all coding agents (Claude Code, Aider, etc.)"""
    
    @abstractmethod
    def initialize(self, config: dict) -> None:
        """Initialize agent with configuration"""
        pass
    
    @abstractmethod
    def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
        """Send prompt to agent and return response"""
        pass
    
    # ... implement all methods from plan
    
class LLMPlugin(ABC):
    """Abstract base class for local LLM providers"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text completion"""
        pass
    
    # ... implement all methods from plan
```

**Read the full specification in:**
- `plans/00_architecture_overview.json` → deliverables → 0.1

**Acceptance criteria:**
- Can subclass and implement all abstract methods
- Type checking passes (mypy)
- Docstrings explain purpose, params, returns, raises
- Examples in docstrings are runnable

### Step 6: Implement Deliverable 0.2 - Plugin Registry

**File: `src/plugins/registry.py`**

**What to build:**
```python
class AgentRegistry:
    """Registry for agent plugins with decorator-based registration"""
    
    _agents = {}
    
    @classmethod
    def register(cls, name: str, agent_class: type):
        """Register an agent plugin"""
        cls._agents[name] = agent_class
    
    # ... implement all methods from plan

def register_agent(name: str):
    """Decorator for auto-registration"""
    def decorator(agent_class):
        AgentRegistry.register(name, agent_class)
        return agent_class
    return decorator
```

**Read the full specification in:**
- `plans/00_architecture_overview.json` → deliverables → 0.2

### Step 7: Implement Deliverable 0.3 - Documentation

Create architecture documentation:

**Files to create:**
1. `docs/architecture/system_design.md`
2. `docs/architecture/plugin_system.md`
3. `docs/architecture/data_flow.md`
4. `docs/decisions/001_why_plugins.md`
5. `docs/decisions/002_deployment_models.md`
6. `docs/decisions/003_state_management.md`

**Read the content requirements in:**
- `plans/00_architecture_overview.json` → deliverables → 0.3

## Critical Implementation Guidelines

### Code Standards
```python
# ✅ ALWAYS use type hints
def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    pass

# ✅ ALWAYS add docstrings (Google style)
def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    """Send a prompt to the agent and get response.
    
    Args:
        prompt: The text prompt to send
        context: Optional context dict with task info
        
    Returns:
        Agent's response as string
        
    Raises:
        AgentException: If agent communication fails
    """
    pass

# ✅ ALWAYS validate inputs
if not prompt:
    raise ValueError("Prompt cannot be empty")
```

### Testing Standards
```python
# Write tests alongside code
# tests/test_plugins.py

def test_agent_plugin_interface():
    """Test that AgentPlugin interface is complete"""
    # Verify all abstract methods defined
    # Verify can subclass and implement
    pass

def test_plugin_registration():
    """Test decorator-based registration"""
    @register_agent('test-agent')
    class TestAgent(AgentPlugin):
        pass
    
    assert AgentRegistry.get('test-agent') == TestAgent
```

### Error Handling
```python
# ✅ Use custom exceptions
raise AgentException("Connection failed", context={'host': host})

# ✅ Provide recovery suggestions
raise AgentException(
    "Cannot connect to agent",
    context={'host': host},
    recovery="Check network connectivity and agent process status"
)
```

## Progress Tracking

After completing each deliverable:

1. **Update IMPLEMENTATION_PLAN.md:**
```markdown
| M0: Architecture | 🟡 In Progress | 1/3 deliverables | 2025-11-02 | - | Completed 0.1, working on 0.2 |
```

2. **Run tests:**
```bash
pytest tests/test_plugins.py --cov=src/plugins --cov-report=term
```

3. **Verify coverage meets target (95% for M0)**

4. **Commit with clear message:**
```bash
git commit -m "M0.1: Implement plugin interfaces (AgentPlugin, LLMPlugin)"
```

## Definition of Done for M0

Before moving to M1, verify:

- ✅ All deliverables implemented (0.1, 0.2, 0.3)
- ✅ Tests pass with ≥95% coverage
- ✅ Type checking passes (mypy)
- ✅ Linting passes (pylint ≥9.0)
- ✅ Documentation complete
- ✅ Can instantiate different agent types via config
- ✅ Mock plugins created for testing (EchoAgent, MockAgent)
- ✅ Progress tracked in IMPLEMENTATION_PLAN.md

## After M0: What's Next?

Once M0 is complete, you'll move to **M1 (Foundation)**:
- Database schema (SQLAlchemy models)
- StateManager (single source of truth)
- Configuration management
- Exception hierarchy

**Read ahead:** `plans/01_foundation.json`

## Key Reminders

### What This System Is
- ✅ Local LLM supervises Claude Code
- ✅ Plugin-based (can swap agents)
- ✅ State-driven (everything persisted)
- ✅ Breakpoint-aware (human oversight)

### What This System Is NOT
- ❌ NOT using Anthropic API directly (Claude Code handles that)
- ❌ NOT tracking costs (subscription-based)
- ❌ NOT managing Claude Code's context (it handles its own)

### Critical Architectural Rules
1. **StateManager is single source of truth** - NEVER bypass it
2. **Validation BEFORE quality control** - order matters
3. **Breakpoints at START of iteration** - not end
4. **Plugin interfaces first** - enables everything else
5. **Test alongside code** - not after

## Questions Before Starting?

Read through:
1. ✅ IMPLEMENTATION_PLAN.md (high-level overview)
2. ✅ plans/00_architecture_overview.json (M0 details)
3. ✅ Understand plugin architecture benefits
4. ✅ Understand why this order (M0 before M1)

## Ready to Begin?

**Your first action:**
```bash
# 1. Create project structure
mkdir -p src/plugins tests/mocks docs/architecture docs/decisions config data logs

# 2. Read M0 plan in detail
cat plans/00_architecture_overview.json

# 3. Start with 0.1 - Plugin Interfaces
# Create: src/plugins/base.py
# Implement: AgentPlugin and LLMPlugin abstract base classes

# 4. Write tests as you go
# Create: tests/test_plugins.py
```

**Start implementing deliverable 0.1 now.** After you complete 0.1, report progress and move to 0.2.

Remember: **Quality over speed**. M0 is the foundation for everything else. Get it right.

Good luck! 🚀