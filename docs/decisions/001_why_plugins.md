# ADR-001: Plugin Architecture for Agents and LLMs

## Status
**Accepted** - 2025-11-01

## Context

The orchestrator needs to support multiple agent backends (Claude Code, Aider, custom agents) and potentially multiple LLM providers (Ollama, llama.cpp, vLLM). We need to decide how to structure the codebase to enable this flexibility.

### Options Considered

1. **Hardcode Claude Code integration** (no abstraction)
2. **Add plugin system after MVP**
3. **Implement plugin system from the start**

## Decision

We will implement a plugin architecture from the beginning using:
- Abstract base classes (`AgentPlugin`, `LLMPlugin`)
- Registry pattern for discovery
- Decorator-based auto-registration
- Configuration-driven selection

## Rationale

### Why Plugins from the Start?

**Benefits**:
1. **Extensibility**: Can add new agents without modifying core orchestration logic
2. **Testability**: Easy to create mock agents for unit testing
3. **Community**: Enables community contributions of new agents
4. **Flexibility**: Swap implementations via configuration
5. **Maintainability**: Clear separation between core logic and integration code
6. **Future-proof**: Adding plugins later requires 15-20 hours of refactoring

**Costs**:
- +3 hours upfront to design and implement plugin system
- Slightly more complex for first-time contributors
- Need to maintain interface stability

**The math**: 3 hours upfront saves 15-20 hours of refactoring when we inevitably need to support multiple agents.

### Why NOT Wait Until After MVP?

If we hardcode Claude Code and add plugins later:
- Need to refactor all callsites (~50+ locations)
- Risk of breaking existing functionality
- Difficult to ensure all code paths updated
- Postpones the "technical debt tax" but doesn't eliminate it

By implementing plugins now:
- Clean architecture from day one
- Testing is easier (can use mocks)
- Second agent takes <4 hours instead of 20+

### Industry Precedent

This pattern is proven in similar tools:
- **Airflow**: Operator plugins for different services
- **Jenkins**: Plugin architecture for extensibility
- **Terraform**: Provider plugins
- **pytest**: Plugin system via entry points

All of these could have launched faster with hardcoded integrations, but chose plugins for long-term maintainability.

## Consequences

### Positive

✅ **Can swap agents via config**:
```yaml
agent:
  type: claude-code-ssh  # change to 'aider' without code changes
```

✅ **Easy testing**:
```python
agent = MockAgent()  # No SSH/Docker needed for unit tests
agent.set_response("Expected output")
```

✅ **Community contributions**:
- Others can add new agents without touching core code
- Submit plugin as standalone module
- Clear interface contract to follow

✅ **Multiple deployment models**:
- ClaudeCodeSSHAgent (VM via SSH)
- ClaudeCodeDockerAgent (container)
- ClaudeCodeLocalAgent (subprocess)
- Same interface, different isolation levels

✅ **Professional codebase**:
- Industry-standard architecture
- Easy for experienced developers to understand
- Follows SOLID principles (especially Open/Closed)

### Negative

❌ **Slight learning curve**:
- New contributors need to understand plugin system
- More files to navigate initially
- **Mitigation**: Comprehensive documentation (done in M0)

❌ **Interface stability required**:
- Breaking changes to AgentPlugin affect all implementations
- Need to version interfaces if major changes needed
- **Mitigation**: Start with minimal interface, add optional methods

❌ **Upfront time investment**:
- 3 hours to implement properly
- **Mitigation**: This is M0's only focus, time well-spent

## Implementation Details

### Plugin Interfaces

Two abstract base classes:
- `AgentPlugin`: Interface for coding agents
- `LLMPlugin`: Interface for LLM providers

### Registry System

Two registries with thread-safe operations:
- `AgentRegistry`: Manages agent plugins
- `LLMRegistry`: Manages LLM plugins

### Auto-Registration

Decorators for convenience:
```python
@register_agent('my-agent')
class MyAgent(AgentPlugin):
    # Implementation
```

### Configuration-Driven

Plugins selected via YAML config, not code:
```yaml
orchestrator:
  agent:
    type: claude-code-ssh
```

## Alternatives Considered

### Alternative 1: Hardcode Claude Code

**Description**: Directly integrate Claude Code without abstraction layer.

**Pros**:
- Faster initial implementation (-3 hours)
- Simpler code initially
- Fewer files

**Cons**:
- Cannot support other agents
- Difficult to test (always need SSH/VM)
- Refactoring cost when we need flexibility: 15-20 hours
- Not extensible for community

**Why Rejected**: False economy. We pay much more later, and testing is harder throughout development.

### Alternative 2: Strategy Pattern Only (No Registry)

**Description**: Use strategy pattern but no automatic discovery/registration.

**Pros**:
- Simpler than full plugin system
- Still provides abstraction

**Cons**:
- Manual wiring required (no config-driven selection)
- No runtime discovery of available plugins
- Less flexible

**Why Rejected**: Registry adds only ~1 hour but provides significant value (config-driven selection, plugin discovery).

### Alternative 3: Add Plugins in M2

**Description**: Start with hardcoded Claude Code, add plugin system in M2.

**Pros**:
- Faster M0 completion
- Can validate orchestration logic first

**Cons**:
- M2 becomes much more complex (16-18 hours instead of 10)
- High risk of bugs during refactoring
- All M1 tests need updating
- Requires touching every file that interacts with agent

**Why Rejected**: Refactoring is risky and time-consuming. Better to get architecture right in M0.

## Validation

This decision will be validated by:
1. ✅ Can create mock agent in <30 minutes (M0 test)
2. ✅ Can swap agents via config change only (M2 test)
3. ⏳ Second agent implementation takes <4 hours (M7 test)
4. ⏳ Community member can add new agent (post-v1.0)

## Notes

- Plugin interfaces defined in `src/plugins/base.py`
- Registry implementation in `src/plugins/registry.py`
- Documentation in `docs/architecture/plugin_system.md`
- Example implementations in `tests/mocks/` (M0) and `src/agents/` (M2+)

## References

- [Plugin System Design Document](../architecture/plugin_system.md)
- [M0 Implementation Plan](../../plans/00_architecture_overview.json)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID) - Especially Open/Closed Principle
- [Airflow Plugin Architecture](https://airflow.apache.org/docs/apache-airflow/stable/plugins.html)

---
**Decision Date**: 2025-11-01
**Decision Makers**: Project Lead
**Status**: Implemented in M0
