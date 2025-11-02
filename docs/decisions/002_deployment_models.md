# ADR-002: Multiple Deployment Models via Plugin Implementations

## Status
**Accepted** - 2025-11-01

## Context

Claude Code needs to run in different environments depending on user needs:
- **Safety**: Some users need maximum isolation (dangerous mode can execute arbitrary code)
- **Ease of use**: Others want simple one-command setup
- **Development**: Developers need fast iteration cycles

We need to decide how to support these different deployment scenarios.

## Decision

We will support multiple deployment models through separate `AgentPlugin` implementations:
1. **ClaudeCodeSSHAgent**: Claude Code in VM via SSH (primary)
2. **ClaudeCodeDockerAgent**: Claude Code in container
3. **ClaudeCodeLocalAgent**: Claude Code as subprocess (development only)

All use the same `AgentPlugin` interface - users select via configuration.

## Rationale

### Why Multiple Deployment Models?

Different users have different priorities:

| User Type | Priority | Best Deployment |
|-----------|----------|----------------|
| Power user (dangerous mode) | Safety | SSH to VM |
| Casual user | Ease of use | Docker |
| Developer (this project) | Iteration speed | Local subprocess |
| Enterprise | Compliance | Docker with network isolation |

A single deployment model can't satisfy all needs.

### Why Separate Plugin Implementations?

**Alternative**: One agent class with mode parameter

```python
agent = ClaudeCodeAgent(mode='ssh')  # vs Docker vs local
```

**Why NOT this**:
- Violates Single Responsibility Principle
- SSH and Docker have very different dependencies
- Testing requires all dependencies installed
- Configuration schemas differ significantly

**Better**: Separate classes

```python
# SSH implementation
agent = ClaudeCodeSSHAgent()

# Docker implementation
agent = ClaudeCodeDockerAgent()
```

**Benefits**:
- Each class has single responsibility
- Can install only needed dependencies
- Clear separation of concerns
- Easier to test in isolation

## Deployment Model Details

### Model 1: SSH to VM (Primary)

**Use Case**: Maximum safety with dangerous mode

**How it works**:
```
Host (Windows 11) → SSH → WSL2 VM → Claude Code CLI
```

**Pros**:
- ✅ Full isolation (VM can be destroyed/restored)
- ✅ SSH is reliable and well-understood
- ✅ Can run Claude Code dangerous mode safely
- ✅ Network-accessible (can be remote VM)

**Cons**:
- ❌ Requires VM setup
- ❌ 50-200ms network latency per operation
- ❌ SSH key management

**Configuration**:
```yaml
agent:
  type: claude-code-ssh
  config:
    host: 192.168.1.100
    user: claude
    key_path: ~/.ssh/vm_key
    workspace_path: /home/claude/workspace
```

**Implementation**: M2 (high priority)

**Dependencies**: `paramiko` (SSH library)

### Model 2: Docker Container

**Use Case**: Easy distribution, good isolation

**How it works**:
```
Host → Docker API → Container → Claude Code CLI
```

**Pros**:
- ✅ Easy distribution (`docker-compose up`)
- ✅ Reproducible environment
- ✅ Good isolation (container boundary)
- ✅ No network latency
- ✅ Resource limits (CPU, memory)

**Cons**:
- ❌ Requires Docker installed
- ❌ Container management complexity
- ❌ Slightly slower than local (container overhead)

**Configuration**:
```yaml
agent:
  type: claude-code-docker
  config:
    image: claude-code:latest
    workspace_mount: ./workspace
    container_name: claude-agent
```

**Implementation**: M7 (for distribution)

**Dependencies**: `docker` (Python SDK)

### Model 3: Local Subprocess

**Use Case**: Development and testing

**How it works**:
```
Host → subprocess.Popen → Claude Code CLI
```

**Pros**:
- ✅ Fastest (no network/container overhead)
- ✅ Simplest setup
- ✅ Direct file access
- ✅ Easy debugging

**Cons**:
- ❌ No isolation (agent has full host access)
- ❌ NOT SAFE for dangerous mode
- ❌ Platform-specific paths

**Configuration**:
```yaml
agent:
  type: claude-code-local
  config:
    workspace_path: ./workspace
    claude_code_path: /usr/local/bin/claude-code
```

**Implementation**: Optional (M2 or later)

**Dependencies**: None (stdlib `subprocess`)

**WARNING**: Only for development. Never use with dangerous mode!

## Implementation Priority

### Phase 1 (M2): SSH Implementation
- Primary deployment model
- Enables safe dangerous mode
- Most complex, implement first

### Phase 2 (M7): Docker Implementation
- For distribution and easy setup
- Leverage lessons from SSH implementation
- Include in distribution package

### Phase 3 (Optional): Local Implementation
- If needed for development workflow
- Simplest to implement
- Can be community contribution

## Configuration-Driven Selection

Users select deployment model via config:

```yaml
orchestrator:
  agent:
    type: claude-code-ssh  # or docker, or local
    config:
      # Model-specific config here
```

Orchestrator code never changes:

```python
# Load agent from config
agent_type = config.get('orchestrator.agent.type')
agent_class = AgentRegistry.get(agent_type)
agent = agent_class()
agent.initialize(config.get('orchestrator.agent.config'))
```

## Trade-Offs Comparison

| Aspect | SSH | Docker | Local |
|--------|-----|--------|-------|
| **Safety** | Excellent | Very Good | None |
| **Performance** | Good (50-200ms latency) | Excellent | Excellent |
| **Setup Complexity** | Medium | Low | Very Low |
| **Isolation** | VM boundary | Container | None |
| **Distribution** | Manual | Easy (docker-compose) | Manual |
| **Debugging** | Moderate | Moderate | Easy |
| **Resource Usage** | High (VM) | Medium (container) | Low |
| **Platform Support** | Any with SSH | Docker-supported | Platform-specific |

## Consequences

### Positive

✅ **Users choose their priority**:
- Safety-focused → SSH
- Ease-focused → Docker
- Speed-focused → Local (dev only)

✅ **Future-proof**:
- Can add new deployment models (K8s, cloud VMs, etc.)
- Same plugin interface
- No core code changes

✅ **Testing flexibility**:
- Use MockAgent for unit tests
- Use LocalAgent for integration tests
- Use SSH/Docker for e2e tests

✅ **Clear documentation**:
- Each deployment model has clear use case
- Users know trade-offs
- No "one size fits all" compromise

### Negative

❌ **Multiple codepaths to maintain**:
- Each deployment model needs testing
- Bug fixes may need to be applied to multiple implementations
- **Mitigation**: Shared base class for common logic

❌ **Documentation overhead**:
- Need to document each deployment model
- Setup instructions differ
- **Mitigation**: Separate guide per model (done)

❌ **User confusion**:
- Which model should I use?
- **Mitigation**: Clear decision matrix in docs

## Alternatives Considered

### Alternative 1: SSH Only

**Description**: Only support SSH deployment.

**Pros**:
- Simplest to implement (one model)
- Clear safety story

**Cons**:
- Higher barrier to entry (VM setup required)
- Slower for casual users
- No easy distribution story

**Why Rejected**: Too limiting for users who prioritize ease over safety.

### Alternative 2: Docker Only

**Description**: Only support Docker deployment.

**Pros**:
- Easy distribution
- Good balance of safety and ease

**Cons**:
- Some users don't use Docker
- Container overhead for simple tasks
- Harder to debug than local

**Why Rejected**: Doesn't support maximum isolation (VM boundary) for dangerous mode.

### Alternative 3: Plugin for Each Variation

**Description**: Separate plugins for SSH-VM, SSH-Remote, Docker, Docker-Compose, Local, etc.

**Pros**:
- Maximum flexibility

**Cons**:
- Too many plugins to maintain
- User confusion (too many choices)
- Most combinations not meaningfully different

**Why Rejected**: Over-engineering. Three models cover all real use cases.

## Validation

This decision will be validated by:
1. ✅ Can switch between models via config only (M2 test)
2. ⏳ SSH model works reliably for dangerous mode (M2)
3. ⏳ Docker model works with single command setup (M7)
4. ⏳ Users report deployment model meets their needs (post-v1.0 survey)

## Security Considerations

### SSH Model
- Use key-based auth (never password)
- VM should not have access to host filesystem
- Dedicated VM user with limited permissions
- Network isolation (separate subnet)

### Docker Model
- Use minimal base image
- Don't run as root in container
- Limit resources (CPU, memory, network)
- Mount workspace read-only when possible
- No --privileged flag

### Local Model
- **⚠️ NEVER USE WITH DANGEROUS MODE ⚠️**
- Development/testing only
- Clearly warn in documentation
- Don't include in production deployments

## References

- [Plugin System ADR](./001_why_plugins.md)
- [SSH Security Best Practices](https://www.ssh.com/academy/ssh/security)
- [Docker Security](https://docs.docker.com/engine/security/)
- [M2 Implementation Plan](../../plans/02_interfaces.json)

---
**Decision Date**: 2025-11-01
**Decision Makers**: Project Lead
**Status**: Planned (M2 for SSH, M7 for Docker)
